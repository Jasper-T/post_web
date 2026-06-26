<template>
  <div class="file-upload-manager" :class="{ open: visible }">
    <button
      class="small-button icon-button file-upload-trigger"
      type="button"
      aria-label="Upload files"
      title="Upload files or folders"
      :disabled="!targetAllowed"
      @click="visible = !visible"
    >
      <svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 16V4M7 9l5-5 5 5M5 14v5h14v-5" />
      </svg>
    </button>

    <div v-if="visible" class="file-upload-popover" @click.stop>
      <div class="file-upload-header">
        <div>
          <strong>上传</strong>
          <small :title="targetPath">{{ targetPath || "请先选择数据集目录内的项目" }}</small>
        </div>
        <button class="small-button icon-button" type="button" aria-label="Close upload panel" @click="visible = false">
          <svg class="button-icon upload-close-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg>
        </button>
      </div>

      <div
        class="file-upload-dropzone"
        :class="{ dragging }"
        @dragenter.prevent="dragging = true"
        @dragover.prevent="dragging = true"
        @dragleave.prevent="handleDragLeave"
        @drop.prevent="handleDrop"
      >
        <strong>拖拽文件或文件夹到这里</strong>
        <span>支持所有文件类型</span>
        <div class="file-upload-choice-row">
          <button class="small-button" type="button" :disabled="!targetAllowed" @click="fileInput?.click()">选择文件</button>
          <button class="small-button" type="button" :disabled="!targetAllowed" @click="folderInput?.click()">选择文件夹</button>
        </div>
        <input ref="fileInput" class="visually-hidden" type="file" multiple @change="handleFileInput" />
        <input ref="folderInput" class="visually-hidden" type="file" multiple webkitdirectory directory @change="handleFolderInput" />
      </div>

      <div v-if="items.length" class="file-upload-progress-summary">
        <div>
          <span>总体进度</span>
          <strong>{{ overallPercent }}%</strong>
        </div>
        <div class="upload-progress-track"><span :style="{ width: overallPercent + '%' }"></span></div>
        <small>{{ completedCount }}/{{ items.length }} 完成 · {{ formatBytes(totalLoaded) }}/{{ formatBytes(totalBytes) }}</small>
      </div>

      <div v-if="items.length" class="file-upload-actions">
        <button class="small-button" type="button" :disabled="!hasActiveItems" @click="cancelAll">全部取消</button>
        <button class="small-button" type="button" :disabled="!hasFailedItems" @click="retryFailed">重试失败项</button>
        <button class="small-button" type="button" :disabled="hasActiveItems" @click="clearFinished">清空列表</button>
      </div>

      <div v-if="items.length" class="file-upload-list">
        <article v-for="item in items" :key="item.id" class="file-upload-item" :class="item.status">
          <div class="file-upload-item-title">
            <strong :title="item.relativePath">{{ item.relativePath }}</strong>
            <span>{{ statusText(item) }}</span>
          </div>
          <div class="upload-progress-track small"><span :style="{ width: item.percent + '%' }"></span></div>
          <div class="file-upload-item-meta">
            <small>{{ formatBytes(item.loaded) }}/{{ formatBytes(item.size) }}</small>
            <small v-if="item.error" class="upload-error" :title="item.error">{{ item.error }}</small>
            <button v-if="item.status === 'uploading' || item.status === 'pending'" class="upload-inline-action" type="button" @click="cancelItem(item)">取消</button>
            <button v-else-if="item.status === 'failed' || item.status === 'canceled'" class="upload-inline-action" type="button" @click="retryItem(item)">重试</button>
          </div>
        </article>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  targetPath: { type: String, default: "" },
});
const emit = defineEmits(["uploaded"]);

const concurrency = 3;
const visible = ref(false);
const dragging = ref(false);
const fileInput = ref(null);
const folderInput = ref(null);
const items = ref([]);
const activeRequests = new Map();
const uploadedResults = [];
let nextId = 1;

const normalizedTargetPath = computed(() => normalizePath(props.targetPath));
const targetAllowed = computed(() => Boolean(normalizedTargetPath.value));
const totalBytes = computed(() => items.value.reduce((sum, item) => sum + item.size, 0));
const totalLoaded = computed(() => items.value.reduce((sum, item) => sum + Math.min(item.loaded, item.size), 0));
const overallPercent = computed(() => totalBytes.value ? Math.round(totalLoaded.value * 100 / totalBytes.value) : (items.value.length && completedCount.value === items.value.length ? 100 : 0));
const completedCount = computed(() => items.value.filter((item) => item.status === "success").length);
const hasActiveItems = computed(() => items.value.some((item) => item.status === "pending" || item.status === "uploading"));
const hasFailedItems = computed(() => items.value.some((item) => item.status === "failed" || item.status === "canceled"));

function normalizePath(value) {
  let path = String(value || "").split("\\").join("/");
  while (path.length > 1 && path.endsWith("/")) path = path.slice(0, -1);
  return path;
}

function handleFileInput(event) {
  enqueueFiles(Array.from(event.target.files || []), (file) => file.name);
  event.target.value = "";
}

function handleFolderInput(event) {
  enqueueFiles(Array.from(event.target.files || []), (file) => file.webkitRelativePath || file.name);
  event.target.value = "";
}

function enqueueFiles(files, relativePathFor) {
  if (!targetAllowed.value || !files.length) return;
  for (const file of files) {
    items.value.push(createUploadItem(file, relativePathFor(file)));
  }
  pumpQueue();
}

function createUploadItem(file, relativePath) {
  return {
    id: nextId++, file, relativePath: normalizeRelativePath(relativePath), size: file.size,
    loaded: 0, percent: 0, status: "pending", error: "", result: null,
  };
}

function normalizeRelativePath(value) {
  return String(value || "").split("\\").join("/").split("/").filter((part) => part && part !== "." && part !== "..").join("/");
}

function pumpQueue() {
  while (activeRequests.size < concurrency) {
    const next = items.value.find((item) => item.status === "pending");
    if (!next) break;
    uploadItem(next);
  }
  notifyIdle();
}

function uploadItem(item) {
  item.status = "uploading";
  item.error = "";
  const query = new URLSearchParams({ directory: props.targetPath, relative_path: item.relativePath });
  const xhr = new XMLHttpRequest();
  activeRequests.set(item.id, xhr);
  xhr.open("POST", "/api/files/upload?" + query.toString());
  xhr.setRequestHeader("Content-Type", item.file.type || "application/octet-stream");
  xhr.upload.onprogress = (event) => {
    if (!event.lengthComputable) return;
    item.loaded = event.loaded;
    item.percent = event.total ? Math.round(event.loaded * 100 / event.total) : 0;
  };
  xhr.onload = () => {
    activeRequests.delete(item.id);
    if (xhr.status >= 200 && xhr.status < 300) {
      item.result = JSON.parse(xhr.responseText || "{}");
      item.status = "success";
      item.loaded = item.size;
      item.percent = 100;
      uploadedResults.push(item.result);
    } else {
      item.status = "failed";
      item.error = responseError(xhr);
    }
    pumpQueue();
  };
  xhr.onerror = () => finishFailed(item, "网络错误");
  xhr.onabort = () => {
    activeRequests.delete(item.id);
    item.status = "canceled";
    item.error = "已取消";
    pumpQueue();
  };
  xhr.send(item.file);
}

function finishFailed(item, message) {
  activeRequests.delete(item.id);
  item.status = "failed";
  item.error = message;
  pumpQueue();
}

function responseError(xhr) {
  try {
    const detail = JSON.parse(xhr.responseText || "{}").detail;
    return typeof detail === "string" ? detail : "上传失败 (" + xhr.status + ")";
  } catch {
    return "上传失败 (" + xhr.status + ")";
  }
}

function cancelItem(item) {
  const request = activeRequests.get(item.id);
  if (request) request.abort();
  else if (item.status === "pending") {
    item.status = "canceled";
    item.error = "已取消";
    pumpQueue();
  }
}

function cancelAll() {
  for (const item of items.value) {
    if (item.status === "pending" || item.status === "uploading") cancelItem(item);
  }
}

function retryItem(item) {
  item.loaded = 0;
  item.percent = 0;
  item.error = "";
  item.result = null;
  item.status = "pending";
  pumpQueue();
}

function retryFailed() {
  for (const item of items.value) {
    if (item.status === "failed" || item.status === "canceled") {
      item.loaded = 0; item.percent = 0; item.error = ""; item.result = null; item.status = "pending";
    }
  }
  pumpQueue();
}

function clearFinished() {
  items.value = [];
  uploadedResults.length = 0;
}

function notifyIdle() {
  if (activeRequests.size || items.value.some((item) => item.status === "pending")) return;
  if (uploadedResults.length) {
    emit("uploaded", { directory: props.targetPath, items: uploadedResults.splice(0) });
  }
}

async function handleDrop(event) {
  dragging.value = false;
  if (!targetAllowed.value) return;
  const transferItems = Array.from(event.dataTransfer?.items || []);
  const entries = transferItems.map((item) => item.webkitGetAsEntry?.()).filter(Boolean);
  if (entries.length) {
    const dropped = [];
    for (const entry of entries) await collectEntryFiles(entry, "", dropped);
    enqueueFiles(dropped.map((item) => item.file), (file) => dropped.find((item) => item.file === file)?.relativePath || file.name);
    return;
  }
  enqueueFiles(Array.from(event.dataTransfer?.files || []), (file) => file.name);
}

function handleDragLeave(event) {
  if (!event.currentTarget.contains(event.relatedTarget)) dragging.value = false;
}

async function collectEntryFiles(entry, prefix, output) {
  if (entry.isFile) {
    const file = await new Promise((resolve, reject) => entry.file(resolve, reject));
    output.push({ file, relativePath: prefix + entry.name });
    return;
  }
  if (!entry.isDirectory) return;
  const nextPrefix = prefix + entry.name + "/";
  const reader = entry.createReader();
  while (true) {
    const entries = await new Promise((resolve, reject) => reader.readEntries(resolve, reject));
    if (!entries.length) break;
    for (const child of entries) await collectEntryFiles(child, nextPrefix, output);
  }
}

function statusText(item) {
  return { pending: "等待中", uploading: item.percent + "%", success: item.result?.renamed ? "完成（已重命名）" : "完成", failed: "失败", canceled: "已取消" }[item.status] || item.status;
}

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  if (bytes < 1024 * 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + " MB";
  return (bytes / 1024 / 1024 / 1024).toFixed(1) + " GB";
}
</script>
