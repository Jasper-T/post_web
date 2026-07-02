<template>
  <li class="ui-tree-branch">
    <div
      class="tree-row ui-list-item ui-tree-node"
      :class="{ selected: selectedPath === node.path, 'upload-selected': highlightPath === node.path }"
      :style="{ paddingLeft: `${level * 16 + 8}px` }"
      @click="handleClick"
      @dblclick="selectNode"
    >
      <button
        v-if="node.type === 'directory'"
        class="tree-toggle ui-tree-toggle ui-icon-collapse ui-icon-btn"
        type="button"
        :disabled="node.loading || !node.hasChildren"
        @click.stop="toggleNode"
      >
        <span v-if="node.loading">...</span>
        <span v-else-if="!node.hasChildren">&nbsp;</span>
        <svg
          v-else-if="node.expanded"
          class="tree-toggle-icon"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
        <svg
          v-else
          class="tree-toggle-icon"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path d="M9 6l6 6-6 6" />
        </svg>
      </button>
      <span v-else class="tree-toggle tree-toggle-placeholder ui-tree-toggle ui-icon-collapse ui-icon-btn"></span>

      <svg
        v-if="node.type === 'directory'"
        class="tree-icon folder-icon ui-tree-icon"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          d="M3 6.5A2.5 2.5 0 0 1 5.5 4h4.1l2 2H18.5A2.5 2.5 0 0 1 21 8.5v8A2.5 2.5 0 0 1 18.5 19h-13A2.5 2.5 0 0 1 3 16.5v-10Z"
          fill="currentColor"
        />
      </svg>
      <svg
        v-else
        class="tree-icon file-icon ui-tree-icon"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          d="M6 3h8l4 4v14H6V3Zm7 1.5V8h3.5L13 4.5Z"
          fill="currentColor"
        />
      </svg>
      <span class="tree-name ui-tree-label" :title="node.path">{{ node.name }}</span>
    </div>

    <p v-if="node.error" class="tree-error" :style="{ paddingLeft: `${level * 16 + 32}px` }">
      {{ node.error }}
    </p>

    <ul v-if="node.expanded && node.children?.length" class="tree-list ui-tree-children">
      <TreeNode
        v-for="child in node.children"
        :key="child.path"
        :node="child"
        :level="level + 1"
        :selected-path="selectedPath"
        :highlight-path="highlightPath"
        :hide-load-more="hideLoadMore"
        @select="$emit('select', $event)"
        @highlight="$emit('highlight', $event)"
        @toggle="$emit('toggle', $event)"
        @load-more="$emit('load-more', $event)"
        @add="$emit('add', $event)"
      />
      <li v-if="node.hasMoreChildren && !hideLoadMore">
        <button
          class="ui-btn ui-tree-load-more"
          type="button"
          :style="{ paddingLeft: `${(level + 1) * 16 + 30}px` }"
          :disabled="node.loadingMore"
          @click="$emit('load-more', node)"
        >
          {{ node.loadingMore ? "loading..." : "..." }}
        </button>
      </li>
    </ul>
  </li>
</template>

<script setup>
defineOptions({ name: "TreeNode" });

const props = defineProps({
  node: {
    type: Object,
    required: true,
  },
  level: {
    type: Number,
    default: 0,
  },
  selectedPath: {
    type: String,
    default: "",
  },
  highlightPath: {
    type: String,
    default: "",
  },
  hideLoadMore: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["select", "highlight", "toggle", "load-more", "add"]);

function handleClick() {
  emit("highlight", originalNode());
  if (originalNode().type === "directory") {
    emit("toggle", originalNode());
  }
}

function selectNode() {
  emit("select", originalNode());
}

function toggleNode() {
  emit("toggle", originalNode());
}

function addNode() {
  emit("add", originalNode());
}

function originalNode() {
  return props.node.sourceNode ?? props.node;
}
</script>
