<template>
  <main class="image-page-shell">
    <section class="image-page-left">
      <FileSystemTree
        :root-node="rootNode"
        :selected-path="activePath"
        title="文件系统"
        loading-message="正在加载根目录..."
        :filter-loader="fetchFilteredChildren"
        @refresh="reloadRoot"
        @select="selectPath"
        @toggle="toggleNode"
        @load-more="loadMoreChildren"
      />
    </section>

    <section class="panel image-preview-panel">
      <header class="panel-header">
        <div>
          <p class="eyebrow">Image Preview</p>
          <h2>图片预览</h2>
        </div>
      </header>

      <div class="image-preview-body">
        <section
          class="image-stage-section"
          :class="{ 'viewer-active': keyboardEnabled }"
          @mousedown="activateKeyboard"
        >
          <div class="image-stage-header">
            <div class="image-stage-title">
              {{ currentImage?.name || "未选择图片" }}
            </div>
            <div class="image-stage-meta">
              <span>{{ currentIndexText }}</span>
              <span>{{ zoomText }}</span>
            </div>
          </div>

          <div
            ref="viewerRef"
            class="image-stage"
            :class="{ dragging: isDragging, zoomed: zoom > 1 }"
            tabindex="0"
            @focus="keyboardEnabled = true"
            @blur="keyboardEnabled = false"
            @keydown.left.prevent="showPreviousImage"
            @keydown.right.prevent="showNextImage"
            @wheel.prevent="handleWheel"
            @pointerdown="handleImagePointerDown"
            @pointermove="handleImagePointerMove"
            @pointerup="handleImagePointerUp"
            @pointerleave="handleImagePointerUp"
            @pointercancel="handleImagePointerUp"
          >
            <template v-if="currentImage">
              <button
                v-if="hasPrevious"
                class="image-nav-button left"
                type="button"
                aria-label="Previous image"
                @click="showPreviousImage"
              >
                <
              </button>

              <img
                ref="imageRef"
                class="preview-image"
                :class="{ draggable: zoom > 1 }"
                :src="imageSource(currentImage.path)"
                :alt="currentImage.name"
                :style="imageTransformStyle"
                draggable="false"
                @load="handleImageLoad"
              />

              <button
                v-if="hasNext"
                class="image-nav-button right"
                type="button"
                aria-label="Next image"
                @click="showNextImage"
              >
                >
              </button>
            </template>

            <div v-else class="empty-state compact-empty-state">
              {{ emptyMessage }}
            </div>
          </div>
        </section>

        <aside class="image-info-sidebar" @mousedown="keyboardEnabled = false">
          <div class="image-info-row">
            <span class="image-info-label">所在文件夹</span>
            <div class="image-info-value">{{ gallery.directoryPath || "-" }}</div>
          </div>

          <div class="image-info-row">
            <span class="image-info-label">图片尺寸</span>
            <div class="image-info-value">{{ imageSizeText }}</div>
          </div>

          <PanelListLayout
            eyebrow="Files"
            title="同目录图片"
            :summary="currentIndexText"
          >
            <ReadonlyItemList
              :items="gallery.images"
              :active-value="gallery.selectedPath || ''"
              empty-message="当前目录没有可预览的图片。"
              value-key="path"
              text-key="name"
              @select="handleFileSelect"
              @open="handleFileOpen"
            />
          </PanelListLayout>
        </aside>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import FileSystemTree from "./FileSystemTree.vue";
import PanelListLayout from "./PanelListLayout.vue";
import ReadonlyItemList from "./ReadonlyItemList.vue";

const directoryPageSize = 20;
const filesystemRoot = "/";

const rootNode = ref(createTreeNode({
  name: "/",
  path: filesystemRoot,
  type: "directory",
  hasChildren: true,
}));

const activePath = ref("");
const keyboardEnabled = ref(false);
const viewerRef = ref(null);
const imageRef = ref(null);
const imageWidth = ref(0);
const imageHeight = ref(0);
const zoom = ref(1);
const offsetX = ref(0);
const offsetY = ref(0);
const isDragging = ref(false);
const dragStartX = ref(0);
const dragStartY = ref(0);
const dragOriginX = ref(0);
const dragOriginY = ref(0);
const gallery = ref({
  directoryPath: "",
  selectedPath: null,
  images: [],
});

const currentImageIndex = computed(() => {
  return gallery.value.images.findIndex((item) => item.path === gallery.value.selectedPath);
});

const currentImage = computed(() => {
  return currentImageIndex.value >= 0 ? gallery.value.images[currentImageIndex.value] : null;
});

const hasPrevious = computed(() => currentImageIndex.value > 0);
const hasNext = computed(() => {
  return currentImageIndex.value >= 0 && currentImageIndex.value < gallery.value.images.length - 1;
});

const imageSizeText = computed(() => {
  return imageWidth.value && imageHeight.value ? `${imageWidth.value} x ${imageHeight.value}` : "-";
});

const currentIndexText = computed(() => {
  if (!gallery.value.images.length || currentImageIndex.value < 0) {
    return `0 / ${gallery.value.images.length}`;
  }

  return `${currentImageIndex.value + 1} / ${gallery.value.images.length}`;
});

const zoomText = computed(() => `Zoom ${Math.round(zoom.value * 100)}%`);

const imageTransformStyle = computed(() => ({
  transform: `translate(${offsetX.value}px, ${offsetY.value}px) scale(${zoom.value})`,
}));

const emptyMessage = computed(() => {
  if (!activePath.value) {
    return "从左侧选择一个目录或图片开始。";
  }

  return "当前目录没有可预览的图片，或所选文件不是支持的图片格式。";
});

function createTreeNode(node) {
  return {
    ...node,
    expanded: false,
    loading: false,
    loadingMore: false,
    error: "",
    children: [],
    childrenLoaded: node.childrenLoaded ?? false,
    childrenOffset: node.childrenOffset ?? 0,
    hasMoreChildren: node.hasMoreChildren ?? false,
  };
}

async function fetchRawChildren(path, offset = 0, limit = directoryPageSize, filter = "") {
  const params = new URLSearchParams({
    path,
    offset: String(offset),
    limit: String(limit),
  });

  if (filter) {
    params.set("filter", filter);
  }

  const response = await fetch(`/api/tree?${params.toString()}`);
  if (!response.ok) {
    const fallback = `读取失败: ${response.status}`;
    const data = await response.json().catch(() => ({ detail: fallback }));
    throw new Error(data.detail || fallback);
  }

  return response.json();
}

async function fetchChildren(path, offset = 0, filter = "") {
  const data = await fetchRawChildren(path, offset, directoryPageSize, filter);
  return {
    ...data,
    children: data.children.map(createTreeNode),
  };
}

async function fetchFilteredChildren(path, filter) {
  const children = [];
  let offset = 0;
  let hasMore = true;

  while (hasMore) {
    const data = await fetchChildren(path, offset, filter);
    children.push(...data.children);
    offset = data.offset + data.children.length;
    hasMore = data.hasMore;
  }

  return children;
}

async function loadChildren(node, force = false) {
  if (node.type !== "directory" || node.loading) {
    return;
  }

  if (node.childrenLoaded && !force) {
    return;
  }

  node.loading = true;
  node.error = "";

  try {
    const data = await fetchChildren(node.path, force ? 0 : node.childrenOffset);
    node.children = data.children;
    node.childrenOffset = data.offset + data.children.length;
    node.hasMoreChildren = data.hasMore;
    node.childrenLoaded = true;
  } catch (error) {
    node.error = error.message;
  } finally {
    node.loading = false;
  }
}

async function loadMoreChildren(node) {
  if (node.type !== "directory" || node.loadingMore || !node.hasMoreChildren) {
    return;
  }

  node.loadingMore = true;
  node.error = "";

  try {
    const data = await fetchChildren(node.path, node.childrenOffset);
    node.children.push(...data.children);
    node.childrenOffset = data.offset + data.children.length;
    node.hasMoreChildren = data.hasMore;
  } catch (error) {
    node.error = error.message;
  } finally {
    node.loadingMore = false;
  }
}

async function toggleNode(node) {
  if (node.type !== "directory") {
    return;
  }

  node.expanded = !node.expanded;
  if (node.expanded) {
    await loadChildren(node);
  }
}

async function reloadRoot() {
  rootNode.value.childrenLoaded = false;
  rootNode.value.expanded = true;
  await loadChildren(rootNode.value, true);
}

async function selectPath(node) {
  activePath.value = node.path;
  keyboardEnabled.value = false;
  viewerRef.value?.blur();
  await loadGallery(node.path);
}

async function loadGallery(path) {
  resetImageViewport();
  imageWidth.value = 0;
  imageHeight.value = 0;

  try {
    const response = await fetch(`/api/images/browse?${new URLSearchParams({ path }).toString()}`);
    if (!response.ok) {
      gallery.value = { directoryPath: "", selectedPath: null, images: [] };
      return;
    }

    gallery.value = await response.json();
  } catch {
    gallery.value = { directoryPath: "", selectedPath: null, images: [] };
  }
}

function imageSource(path) {
  return `/api/images/content?${new URLSearchParams({ path }).toString()}`;
}

function resetImageViewport() {
  zoom.value = 1;
  offsetX.value = 0;
  offsetY.value = 0;
  isDragging.value = false;
}

function selectImage(path, focusViewer = false) {
  gallery.value = {
    ...gallery.value,
    selectedPath: path,
  };
  imageWidth.value = 0;
  imageHeight.value = 0;
  resetImageViewport();

  if (focusViewer) {
    requestAnimationFrame(() => {
      viewerRef.value?.focus();
    });
  }
}

function handleFileSelect(item) {
  selectImage(item.path);
}

function handleFileOpen(item) {
  selectImage(item.path, true);
}

function showPreviousImage() {
  if (!hasPrevious.value) {
    return;
  }

  selectImage(gallery.value.images[currentImageIndex.value - 1].path, true);
}

function showNextImage() {
  if (!hasNext.value) {
    return;
  }

  selectImage(gallery.value.images[currentImageIndex.value + 1].path, true);
}

function activateKeyboard() {
  viewerRef.value?.focus();
}

function clampOffset() {
  const viewer = viewerRef.value;
  if (!viewer || zoom.value <= 1) {
    offsetX.value = 0;
    offsetY.value = 0;
    return;
  }

  const maxX = Math.max(0, ((viewer.clientWidth * zoom.value) - viewer.clientWidth) / 2);
  const maxY = Math.max(0, ((viewer.clientHeight * zoom.value) - viewer.clientHeight) / 2);
  offsetX.value = Math.min(maxX, Math.max(-maxX, offsetX.value));
  offsetY.value = Math.min(maxY, Math.max(-maxY, offsetY.value));
}

function handleWheel(event) {
  if (!currentImage.value) {
    return;
  }

  const nextZoom = event.deltaY < 0 ? zoom.value + 0.1 : zoom.value - 0.1;
  zoom.value = Math.min(5, Math.max(1, Number(nextZoom.toFixed(2))));
  if (zoom.value === 1) {
    offsetX.value = 0;
    offsetY.value = 0;
  } else {
    clampOffset();
  }
}

function handleImagePointerDown(event) {
  if (zoom.value <= 1 || !currentImage.value) {
    return;
  }

  isDragging.value = true;
  dragStartX.value = event.clientX;
  dragStartY.value = event.clientY;
  dragOriginX.value = offsetX.value;
  dragOriginY.value = offsetY.value;
  event.currentTarget.setPointerCapture?.(event.pointerId);
}

function handleImagePointerMove(event) {
  if (!isDragging.value) {
    return;
  }

  offsetX.value = dragOriginX.value + (event.clientX - dragStartX.value);
  offsetY.value = dragOriginY.value + (event.clientY - dragStartY.value);
  clampOffset();
}

function handleImagePointerUp(event) {
  if (!isDragging.value) {
    return;
  }

  isDragging.value = false;
  event.currentTarget?.releasePointerCapture?.(event.pointerId);
}

function handleImageLoad(event) {
  imageWidth.value = event.target.naturalWidth;
  imageHeight.value = event.target.naturalHeight;
  resetImageViewport();
}

function handlePointerDown(event) {
  const viewer = viewerRef.value;
  if (!viewer) {
    return;
  }

  if (!viewer.contains(event.target)) {
    keyboardEnabled.value = false;
    viewer.blur();
  }
}

onMounted(async () => {
  window.addEventListener("pointerdown", handlePointerDown, true);
  rootNode.value.expanded = true;
  await loadChildren(rootNode.value);
});

onBeforeUnmount(() => {
  window.removeEventListener("pointerdown", handlePointerDown, true);
});
</script>
