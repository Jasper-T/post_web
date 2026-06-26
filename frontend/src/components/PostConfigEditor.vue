<template>
  <div class="post-config-editor">
    <div class="template-editor-toolbar">
      <span class="template-editor-title">请求配置</span>
      <div class="json-template-actions">
        <button class="small-button" type="button" @click="$emit('read')">Read</button>
        <button class="small-button primary-button" type="button" @click="$emit('save')">Save</button>
      </div>
    </div>

    <div class="tab-grid">
      <label class="tool-field">
        <span>Connect Timeout (s)</span>
        <input
          :value="modelValue.connectTimeout"
          type="number"
          min="0.1"
          step="0.1"
          @input="updateField('connectTimeout', Number($event.target.value || 0))"
        />
      </label>
      <label class="tool-field">
        <span>Read Timeout (s)</span>
        <input
          :value="modelValue.readTimeout"
          type="number"
          min="0.1"
          step="0.1"
          @input="updateField('readTimeout', Number($event.target.value || 0))"
        />
      </label>
    </div>

    <div class="mapping-table post-config-table">
      <div class="mapping-head mapping-head-compact">
        <span>Placeholder</span>
        <span>Type</span>
        <span>Inject Path</span>
      </div>
      <div v-for="item in placeholders" :key="item.key" class="mapping-row mapping-row-compact">
        <input class="kv-cell-input" :value="item.key" disabled />
        <select class="kv-cell-input" :value="item.type" @change="updatePlaceholderType(item.key, $event.target.value)">
          <option value="string">string</option>
          <option value="int">int</option>
          <option value="float">float</option>
          <option value="bool">bool</option>
          <option value="array">array</option>
          <option value="object">object</option>
        </select>
        <select class="kv-cell-input" :value="item.path" @change="updatePlaceholder(item.key, $event.target.value)">
          <option value="">None</option>
          <option v-for="path in bodyPathOptions" :key="`${item.key}-${path}`" :value="path">
            {{ path }}
          </option>
        </select>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  modelValue: { type: Object, required: true },
  bodyPathOptions: { type: Array, default: () => [] },
});

const emit = defineEmits(["update:modelValue", "save", "read"]);

const placeholderKeys = ["timestamp", "image_b64", "image_width", "image_height"];

const placeholders = computed(() =>
  placeholderKeys.map((key) => ({
    key,
    path: props.modelValue.placeholderPaths?.[key] || "",
    type: props.modelValue.placeholderTypes?.[key] || "string",
  })),
);

function updateField(key, value) {
  emit("update:modelValue", { ...props.modelValue, [key]: value });
}

function updatePlaceholderType(key, value) {
  emit("update:modelValue", {
    ...props.modelValue,
    placeholderTypes: {
      ...(props.modelValue.placeholderTypes || {}),
      [key]: value,
    },
  });
}

function updatePlaceholder(key, value) {
  emit("update:modelValue", {
    ...props.modelValue,
    placeholderPaths: {
      ...(props.modelValue.placeholderPaths || {}),
      [key]: value || null,
    },
  });
}
</script>
