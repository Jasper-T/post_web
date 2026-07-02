<template>
  <div class="json-preview-tree">
    <div class="json-preview-tree-row">
      <button
        v-if="isExpandable"
        class="json-preview-toggle ui-icon-collapse ui-icon-btn"
        type="button"
        @click="expanded = !expanded"
      >
        {{ expanded ? "-" : "+" }}
      </button>
      <span v-else class="json-preview-toggle-placeholder"></span>

      <div class="json-preview-tree-label">
        <strong>{{ label }}</strong>
        <span class="json-preview-tree-type">{{ typeLabel }}</span>
        <span v-if="!isExpandable" class="json-preview-tree-value">{{ primitiveText }}</span>
      </div>
    </div>

    <div v-if="isExpandable && expanded" class="json-preview-tree-children">
      <JsonPreviewTree
        v-for="child in normalizedChildren"
        :key="child.key"
        :label="child.label"
        :value="child.value"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";

defineOptions({
  name: "JsonPreviewTree",
});

const props = defineProps({
  label: {
    type: String,
    required: true,
  },
  value: {
    type: null,
    required: true,
  },
});

const expanded = ref(true);

const isExpandable = computed(() => {
  return Array.isArray(props.value) || (props.value !== null && typeof props.value === "object");
});

const typeLabel = computed(() => {
  if (Array.isArray(props.value)) {
    return `array(${props.value.length})`;
  }
  if (props.value === null) {
    return "null";
  }
  if (typeof props.value === "object") {
    return "object";
  }
  return typeof props.value;
});

const primitiveText = computed(() => {
  if (typeof props.value === "string") {
    return `"${props.value}"`;
  }
  return String(props.value);
});

const normalizedChildren = computed(() => {
  if (Array.isArray(props.value)) {
    return props.value.map((item, index) => ({
      key: `${props.label}-${index}`,
      label: `[${index}]`,
      value: item,
    }));
  }

  if (props.value !== null && typeof props.value === "object") {
    return Object.entries(props.value).map(([key, value]) => ({
      key: `${props.label}-${key}`,
      label: key,
      value,
    }));
  }

  return [];
});
</script>
