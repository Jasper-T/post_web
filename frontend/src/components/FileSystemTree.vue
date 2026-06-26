<template>
  <section class="panel explorer-panel">
    <header class="panel-header">
      <div>
        <p v-if="eyebrow" class="eyebrow">{{ eyebrow }}</p>
        <h2>{{ title }}</h2>
      </div>
      <div class="header-actions">
        <FileUploadManager
          v-if="showUploadButton"
          :target-path="uploadTargetPath"
          :allowed-root="uploadAllowedRoot"
          @uploaded="$emit('upload-complete', $event)"
        />
        <FileTreeFilterMenu
          :query="activeFilterQuery"
          :extensions="activeExtensions"
          :is-filtering="isFiltering"
          @apply="applyFilter"
        />
        <button
          class="small-button icon-button"
          type="button"
          :aria-label="refreshLabel"
          :disabled="refreshDisabled"
          @click="$emit('refresh')"
        >
          <svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M17.7 6.3A8 8 0 1 0 20 12h-2a6 6 0 1 1-1.76-4.24L13 11h8V3l-3.3 3.3Z"
              fill="currentColor"
            />
          </svg>
        </button>
        <button
          v-if="showAddButton"
          class="small-button icon-button"
          type="button"
          :aria-label="addLabel"
          :disabled="addDisabled"
          @click="$emit('add-current')"
        >
          <svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6V5Z" fill="currentColor" />
          </svg>
        </button>
        <slot name="header-actions"></slot>
      </div>
    </header>

    <div v-if="rootNode" class="tree-container">
      <p v-if="rootNode.error" class="tree-error root-tree-error">
        {{ rootNode.error }}
      </p>
      <div v-if="rootNode.loading" class="empty-state compact-empty-state">
        {{ loadingMessage }}
      </div>
      <div v-else-if="isFiltering" class="empty-state compact-empty-state">
        Filtering...
      </div>
      <div v-else-if="filterError" class="empty-state compact-empty-state">
        {{ filterError }}
      </div>
      <div v-else-if="isFilterActive && !hasFilterResults" class="empty-state compact-empty-state">
        No matches found.
      </div>
      <ul v-else class="tree-list">
        <TreeNode
          v-if="showRootNode"
          :node="displayRootNode"
          :selected-path="selectedPath"
          :highlight-path="highlightPath"
          :hide-load-more="isFilterActive"
          @select="$emit('select', $event)"
          @highlight="$emit('highlight', $event)"
          @toggle="$emit('toggle', $event)"
          @load-more="$emit('load-more', $event)"
          @add="$emit('add-node', $event)"
        />
        <template v-else>
          <TreeNode
            v-for="child in displayChildren"
            :key="child.path"
            :node="child"
            :selected-path="selectedPath"
            :highlight-path="highlightPath"
            :hide-load-more="isFilterActive"
            @select="$emit('select', $event)"
            @highlight="$emit('highlight', $event)"
            @toggle="$emit('toggle', $event)"
            @load-more="$emit('load-more', $event)"
            @add="$emit('add-node', $event)"
          />
          <li v-if="rootNode.hasMoreChildren && !isFilterActive">
            <button
              class="tree-load-more"
              type="button"
              :disabled="rootNode.loadingMore"
              @click="$emit('load-more', rootNode)"
            >
              {{ rootNode.loadingMore ? "loading..." : "..." }}
            </button>
          </li>
        </template>
      </ul>
    </div>
    <div v-else class="empty-state compact-empty-state">
      {{ emptyMessage }}
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from "vue";
import FileTreeFilterMenu from "./FileTreeFilterMenu.vue";
import FileUploadManager from "./FileUploadManager.vue";
import TreeNode from "./TreeNode.vue";

const props = defineProps({
  rootNode: {
    type: Object,
    default: null,
  },
  selectedPath: {
    type: String,
    default: "",
  },
  highlightPath: {
    type: String,
    default: "",
  },
  eyebrow: {
    type: String,
    default: "File System",
  },
  title: {
    type: String,
    default: "File System",
  },
  emptyMessage: {
    type: String,
    default: "No content to display.",
  },
  loadingMessage: {
    type: String,
    default: "Loading...",
  },
  refreshLabel: {
    type: String,
    default: "Refresh",
  },
  addLabel: {
    type: String,
    default: "Add selected item",
  },
  refreshDisabled: {
    type: Boolean,
    default: false,
  },
  showAddButton: {
    type: Boolean,
    default: false,
  },
  showUploadButton: {
    type: Boolean,
    default: false,
  },
  uploadTargetPath: {
    type: String,
    default: "",
  },
  uploadAllowedRoot: {
    type: String,
    default: "/data/datasets",
  },
  addDisabled: {
    type: Boolean,
    default: false,
  },
  showRootNode: {
    type: Boolean,
    default: false,
  },
  filterLoader: {
    type: Function,
    default: null,
  },
});

defineEmits(["refresh", "select", "highlight", "toggle", "load-more", "add-node", "add-current", "upload-complete"]);

const activeFilterQuery = ref("");
const activeExtensions = ref([]);
const isFiltering = ref(false);
const filterError = ref("");
const filteredChildrenByPath = ref(new Map());
let filterRequestId = 0;

const normalizedActiveQuery = computed(() => activeFilterQuery.value.trim().toLowerCase());
const normalizedActiveExtensions = computed(() => activeExtensions.value.map((extension) => extension.toLowerCase()));
const isFilterActive = computed(() => Boolean(normalizedActiveQuery.value) || normalizedActiveExtensions.value.length > 0);

const displayRootNode = computed(() => {
  if (!props.rootNode || !isFilterActive.value) {
    return props.rootNode;
  }

  return filterNode(props.rootNode);
});

const displayChildren = computed(() => {
  if (!props.rootNode) {
    return [];
  }

  if (!isFilterActive.value) {
    return props.rootNode.children;
  }

  return getFilterCandidateChildren(props.rootNode).map(filterNode).filter(Boolean);
});

const hasFilterResults = computed(() => {
  if (!isFilterActive.value) {
    return true;
  }

  if (props.showRootNode) {
    return Boolean(displayRootNode.value);
  }

  return displayChildren.value.length > 0;
});

async function applyFilter(nextFilter) {
  const nextQuery = String(nextFilter?.query || "").trim();
  const nextExtensions = normalizeExtensions(nextFilter?.extensions || []);
  const requestId = ++filterRequestId;

  isFiltering.value = true;
  filterError.value = "";

  try {
    const nextFilteredChildrenByPath = new Map();
    if ((nextQuery || nextExtensions.length > 0) && props.rootNode) {
      await loadFilteredBranches(props.rootNode, nextFilteredChildrenByPath, new Set());
    }

    if (requestId !== filterRequestId) {
      return;
    }

    activeFilterQuery.value = nextQuery;
    activeExtensions.value = nextExtensions;
    filteredChildrenByPath.value = nextFilteredChildrenByPath;
  } catch (error) {
    if (requestId === filterRequestId) {
      filterError.value = error.message || "Filter failed.";
    }
  } finally {
    if (requestId === filterRequestId) {
      isFiltering.value = false;
    }
  }
}

function normalizeExtensions(list) {
  return Array.from(new Set(list.map((extension) => String(extension).toLowerCase()))).sort();
}

function filterNode(node) {
  const children = getFilterCandidateChildren(node).map(filterNode).filter(Boolean);
  const matchesSelf = nodeMatchesFilter(node);

  if (!matchesSelf && children.length === 0) {
    return null;
  }

  return {
    ...node,
    sourceNode: node,
    children,
    expanded: node.expanded || children.length > 0,
    hasMoreChildren: false,
  };
}

async function loadFilteredBranches(node, nextFilteredChildrenByPath, visitedPaths) {
  if (node.type !== "directory" || visitedPaths.has(node.path)) {
    return;
  }

  visitedPaths.add(node.path);

  const directChildren = props.filterLoader
    ? await props.filterLoader(node.path)
    : [...(node.children ?? [])];

  nextFilteredChildrenByPath.set(node.path, directChildren);

  for (const child of directChildren) {
    if (child.type === "directory") {
      await loadFilteredBranches(child, nextFilteredChildrenByPath, visitedPaths);
    }
  }
}

function getFilterCandidateChildren(node) {
  if (!isFilterActive.value) {
    return node.children ?? [];
  }

  const childrenByPath = new Map();
  for (const child of node.children ?? []) {
    childrenByPath.set(child.path, child);
  }

  for (const child of filteredChildrenByPath.value.get(node.path) ?? []) {
    if (!childrenByPath.has(child.path)) {
      childrenByPath.set(child.path, child);
    }
  }

  return Array.from(childrenByPath.values());
}

function nodeMatchesFilter(node) {
  const name = String(node.name ?? "");
  const normalizedName = name.toLowerCase();
  const queryMatches = !normalizedActiveQuery.value || normalizedName.includes(normalizedActiveQuery.value);
  const extensionsActive = normalizedActiveExtensions.value.length > 0;

  if (node.type === "directory") {
    return !extensionsActive && queryMatches;
  }

  const extensionMatches = !extensionsActive || normalizedActiveExtensions.value.some((extension) => normalizedName.endsWith(extension));
  return queryMatches && extensionMatches;
}

onBeforeUnmount(() => {
  filterRequestId += 1;
});
</script>
