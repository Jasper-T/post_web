<template>
  <div class="json-template-editor">
    <div class="template-editor-toolbar json-template-toolbar">
      <span class="template-editor-title">{{ title }}</span>
      <div class="json-template-actions">
        <button class="small-button" type="button" @click="openImportDialog">Import JSON</button>
        <button class="small-button" type="button" @click="addRow">Add Field</button>
        <button class="small-button primary-button" type="button" :disabled="saving" @click="emitSave">
          {{ saving ? "Saving..." : "Save" }}
        </button>
        <button class="small-button" type="button" :disabled="!canPreview" @click="showPreviewDialog = true">
          Preview
        </button>
      </div>
    </div>

    <div class="json-template-grid">
      <section class="json-template-panel">
        <div class="json-template-table">
          <div class="json-template-head">
            <span>Key</span>
            <span>Type</span>
            <span>Value</span>
            <span></span>
          </div>

          <div v-for="(row, index) in rows" :key="row.id" class="json-template-row">
            <input
              class="kv-cell-input"
              :value="row.key"
              placeholder="data.outputs"
              @input="updateRow(index, 'key', $event.target.value)"
            />
            <select class="kv-cell-input" :value="row.type" @change="updateRow(index, 'type', $event.target.value)">
              <option value="string">string</option>
              <option value="number">number</option>
              <option value="boolean">boolean</option>
              <option value="null">null</option>
              <option value="object">object</option>
              <option value="array">array</option>
              <option value="json">json</option>
            </select>
            <input
              class="kv-cell-input"
              :value="row.value"
              :placeholder="valuePlaceholder(row.type)"
              @input="updateRow(index, 'value', $event.target.value)"
            />
            <button class="kv-delete-button" type="button" @click="removeRow(index)">Delete</button>
          </div>
        </div>
      </section>

      <section class="json-template-panel">
        <div class="json-template-preview-scroll">
          <JsonPreviewTree label="root" :value="previewObject" />
        </div>
      </section>
    </div>

    <div v-if="showImportDialog" class="json-import-backdrop" @click.self="closeImportDialog">
      <div class="json-import-dialog">
        <div class="json-import-dialog-header">
          <h4>Import JSON</h4>
          <button class="small-button icon-button" type="button" title="Close" aria-label="Close import dialog" @click="closeImportDialog"><svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg></button>
        </div>
        <div class="json-import-dialog-body">
          <div class="json-import-dialog-inline">
            <span>Paste JSON text</span>
            <button class="small-button primary-button" type="button" @click="applyImport">Parse</button>
          </div>
          <textarea
            v-model="importText"
            class="json-import-textarea"
            rows="14"
            spellcheck="false"
            placeholder='{"name":"demo","meta":{"ok":true}}'
          ></textarea>
          <div v-if="importError" class="tool-alert error">{{ importError }}</div>
        </div>
      </div>
    </div>

    <div v-if="showPreviewDialog" class="json-import-backdrop" @click.self="showPreviewDialog = false">
      <div class="json-import-dialog json-preview-dialog">
        <div class="json-import-dialog-header">
          <h4>Saved JSON</h4>
          <button class="small-button icon-button" type="button" title="Close" aria-label="Close preview dialog" @click="showPreviewDialog = false"><svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg></button>
        </div>
        <pre class="json-template-saved-preview">{{ previewText || "{}" }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import JsonPreviewTree from "./JsonPreviewTree.vue";

const props = defineProps({
  title: { type: String, required: true },
  modelValue: { type: Object, default: () => ({}) },
  canPreview: { type: Boolean, default: false },
  previewText: { type: String, default: "" },
  saving: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue", "save"]);

const rows = ref([]);
const showImportDialog = ref(false);
const showPreviewDialog = ref(false);
const importText = ref("");
const importError = ref("");

watch(
  () => props.modelValue,
  (value) => {
    rows.value = objectToRows(value || {});
  },
  { deep: true, immediate: true },
);

const previewObject = computed(() => rowsToObject(rows.value));

function createRow(partial = {}) {
  return {
    id: partial.id || `json-row-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    key: partial.key || "",
    type: partial.type || "string",
    value: partial.value ?? "",
  };
}

function addRow() {
  rows.value = [...rows.value, createRow()];
  emitChange();
}

function removeRow(index) {
  rows.value = rows.value.filter((_, rowIndex) => rowIndex !== index);
  emitChange();
}

function updateRow(index, key, value) {
  rows.value = rows.value.map((row, rowIndex) => (rowIndex === index ? { ...row, [key]: value } : row));
  emitChange();
}

function emitChange() {
  emit("update:modelValue", rowsToObject(rows.value));
}

function emitSave() {
  emit("save", rowsToObject(rows.value));
}

function openImportDialog() {
  showImportDialog.value = true;
  importError.value = "";
}

function closeImportDialog() {
  showImportDialog.value = false;
  importError.value = "";
}

function applyImport() {
  try {
    const parsed = JSON.parse(importText.value || "{}");
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("JSON root must be an object");
    }
    rows.value = objectToRows(parsed);
    emitChange();
    closeImportDialog();
  } catch (error) {
    importError.value = error.message || "Failed to parse JSON";
  }
}

function objectToRows(source, prefix = "") {
  const entries = [];
  for (const [key, value] of Object.entries(source || {})) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (value !== null && typeof value === "object" && !Array.isArray(value)) {
      entries.push(...objectToRows(value, path));
      continue;
    }
    if (Array.isArray(value)) {
      entries.push(createRow({ key: path, type: Array.isArray(value) ? "array" : "json", value: JSON.stringify(value) }));
      continue;
    }
    entries.push(createRow({ key: path, type: inferType(value), value: stringifyValue(value) }));
  }
  return entries.length ? entries : [createRow()];
}

function inferType(value) {
  if (value === null) {
    return "null";
  }
  if (typeof value === "number") {
    return "number";
  }
  if (typeof value === "boolean") {
    return "boolean";
  }
  return "string";
}

function stringifyValue(value) {
  if (value === null || value === undefined) {
    return "";
  }
  return String(value);
}

function rowsToObject(inputRows) {
  const result = {};
  for (const row of inputRows || []) {
    const path = String(row.key || "").trim();
    if (!path) {
      continue;
    }
    setValueByPath(result, path, parseValue(row.type, row.value));
  }
  return result;
}

function parseValue(type, value) {
  if (type === "number") {
    return value === "" ? 0 : Number(value);
  }
  if (type === "boolean") {
    return value === true || value === "true";
  }
  if (type === "null") {
    return null;
  }
  if (type === "object") {
    return {};
  }
  if (type === "array" || type === "json") {
    return value ? JSON.parse(value) : [];
  }
  return String(value ?? "");
}

function setValueByPath(target, rawPath, value) {
  const parts = String(rawPath || "")
    .split(".")
    .map((item) => item.trim())
    .filter(Boolean);
  if (!parts.length) {
    return;
  }
  let current = target;
  for (const part of parts.slice(0, -1)) {
    if (!current[part] || typeof current[part] !== "object" || Array.isArray(current[part])) {
      current[part] = {};
    }
    current = current[part];
  }
  current[parts[parts.length - 1]] = value;
}

function valuePlaceholder(type) {
  if (type === "array" || type === "json") {
    return "[1,2,3]";
  }
  if (type === "object") {
    return "{}";
  }
  return "value";
}
</script>
