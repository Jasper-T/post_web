<template>
  <section class="json-schema-builder json-schema-summary json-preview-panel ui-panel">
    <header class="json-schema-header json-schema-summary-header json-preview-panel-header ui-panel-header">
      <span class="json-schema-summary-title">{{ previewTitle }}</span>
      <div class="json-schema-header-actions json-preview-panel-actions ui-toolbar">
        <div class="json-preview-mode-toggle ui-segmented" role="tablist" aria-label="Preview Mode">
          <button
            class="json-preview-mode-button"
            :class="{ active: previewMode === 'tree' }"
            type="button"
            role="tab"
            :aria-selected="previewMode === 'tree'"
            @click="previewMode = 'tree'"
          >
            Tree
          </button>
          <button
            class="json-preview-mode-button"
            :class="{ active: previewMode === 'json' }"
            type="button"
            role="tab"
            :aria-selected="previewMode === 'json'"
            @click="previewMode = 'json'"
          >
            JSON
          </button>
        </div>
        <button class="ui-btn ui-btn-primary" type="button" @click="openEditor">Edit</button>
      </div>
    </header>

    <div class="json-preview-card-body json-preview-panel-body ui-panel-body">
      <div v-if="previewMode === 'tree'" class="json-preview-tree-scroll">
        <JsonPreviewTree label="root" :value="displayObject" />
      </div>
      <pre v-else>{{ displayText }}</pre>
    </div>

    <div
      v-if="showEditor"
      class="json-import-backdrop json-schema-editor-backdrop"
      @pointerdown.self="backdropCloseArmed = true"
      @click.self="handleBackdropClick"
    >
      <div class="json-import-dialog json-schema-edit-dialog ui-panel" role="dialog" aria-modal="true" :aria-label="title + ' editor'">
        <div class="json-import-dialog-header json-schema-edit-header ui-panel-header">
          <div>
            <p class="eyebrow">Schema Editor</p>
            <h4>{{ title }}</h4>
            <p>Edit with structured fields or raw JSON.</p>
          </div>
          <button class="ui-action-close ui-icon-close ui-btn ui-icon-btn" type="button" title="Close" aria-label="Close schema editor" @click="closeEditor"><svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg></button>
        </div>

        <div class="json-schema-edit-toolbar ui-toolbar">
          <div class="json-preview-mode-toggle ui-segmented" role="tablist" aria-label="Editor Mode">
            <button
              class="json-preview-mode-button"
              :class="{ active: editorMode === 'tree' }"
              type="button"
              role="tab"
              :aria-selected="editorMode === 'tree'"
              @click="switchEditorMode('tree')"
            >
              Tree
            </button>
            <button
              class="json-preview-mode-button"
              :class="{ active: editorMode === 'json' }"
              type="button"
              role="tab"
              :aria-selected="editorMode === 'json'"
              @click="switchEditorMode('json')"
            >
              JSON
            </button>
          </div>

          <div class="json-schema-edit-actions ui-toolbar">
            <button class="ui-btn" type="button" @click="clearEditor">Clear</button>
            <button class="ui-btn ui-btn-primary" type="button" :disabled="saving" @click="saveEditor">
              {{ saving ? "Saving..." : "Save" }}
            </button>
            <button v-if="editorMode === 'tree'" class="ui-btn" type="button" @click="addRootField">Add Field</button>
          </div>
        </div>

        <div class="json-schema-edit-body">
          <div v-if="editorMode === 'tree'" class="json-schema-editor-scroll">
            <div v-if="!fields.length" class="empty-state compact-empty-state">No fields yet. Click Add Field to begin.</div>
            <JsonFieldEditorRow v-else :fields="fields" />
          </div>

          <textarea
            v-else
            v-model="jsonText"
            class="json-schema-json-editor"
            spellcheck="false"
            aria-label="JSON editor"
          ></textarea>

          <div v-if="editorError" class="tool-alert error">{{ editorError }}</div>
        </div>

      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import JsonFieldEditorRow from "./JsonFieldEditorRow.vue";
import JsonPreviewTree from "./JsonPreviewTree.vue";

const props = defineProps({
  title: {
    type: String,
    default: "JSON Field Builder",
  },
  modelValue: {
    type: Object,
    default: () => ({}),
  },
  savedText: {
    type: String,
    default: "",
  },
  saving: {
    type: Boolean,
    default: false,
  },
  canPreview: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["update:modelValue", "save"]);

const fields = ref([]);
const showEditor = ref(false);
const editorMode = ref("json");
const previewMode = ref("json");
const jsonText = ref("{}");
const editorError = ref("");
const backdropCloseArmed = ref(false);

const previewTitle = computed(() => {
  const baseTitle = String(props.title || "JSON").replace(/\s+JSON$/i, "");
  return `${baseTitle} Preview`;
});
const displayObject = computed(() => readCurrentObject());

const displayText = computed(() => {
  if (props.savedText) {
    return formatJsonText(props.savedText);
  }
  return stringify(props.modelValue || {});
});

const draftObject = computed(() =>
  Object.fromEntries(fields.value.map((field) => [field.name || "field", previewValue(field)])),
);

function openEditor() {
  const source = readCurrentObject();
  fields.value = buildFieldsFromObject(source);
  jsonText.value = stringify(source);
  editorMode.value = "json";
  editorError.value = "";
  showEditor.value = true;
}

function closeEditor() {
  showEditor.value = false;
  editorError.value = "";
  backdropCloseArmed.value = false;
}

function handleBackdropClick() {
  if (backdropCloseArmed.value) {
    closeEditor();
  }
  backdropCloseArmed.value = false;
}

function switchEditorMode(nextMode) {
  if (nextMode === editorMode.value) {
    return;
  }
  editorError.value = "";

  if (nextMode === "json") {
    try {
      validateFields(fields.value);
      jsonText.value = stringify(draftObject.value);
      editorMode.value = "json";
    } catch (error) {
      editorError.value = error.message || "Schema validation failed";
    }
    return;
  }

  try {
    const parsed = parseJsonObject(jsonText.value);
    fields.value = buildFieldsFromObject(parsed);
    jsonText.value = stringify(parsed);
    editorMode.value = "tree";
  } catch (error) {
    editorError.value = error.message || "JSON parse failed";
  }
}

function addRootField() {
  fields.value.push(createField());
}

function clearEditor() {
  editorError.value = "";
  fields.value = [];
  jsonText.value = "{}";
}

function saveEditor() {
  if (props.saving) {
    return;
  }

  editorError.value = "";
  try {
    const payload = editorMode.value === "json" ? parseJsonObject(jsonText.value) : validatedDraftObject();
    fields.value = buildFieldsFromObject(payload);
    jsonText.value = stringify(payload);
    emit("update:modelValue", payload);
    emit("save", payload);
  } catch (error) {
    editorError.value = error.message || "Schema validation failed";
  }
}

function handleSaveShortcut(event) {
  if (!showEditor.value || !(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== "s") {
    return;
  }
  event.preventDefault();
  saveEditor();
}

function validatedDraftObject() {
  validateFields(fields.value);
  return draftObject.value;
}

function readCurrentObject() {
  if (props.savedText) {
    try {
      return parseJsonObject(props.savedText);
    } catch {
      // Fall back to the current in-memory model if saved text is malformed.
    }
  }
  return cloneObject(props.modelValue || {});
}

function formatJsonText(text) {
  try {
    return stringify(JSON.parse(text));
  } catch {
    return text;
  }
}

function parseJsonObject(text) {
  const parsed = JSON.parse(text || "{}");
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("JSON root must be an object.");
  }
  return parsed;
}

function cloneObject(value) {
  return JSON.parse(JSON.stringify(value || {}));
}

function stringify(value) {
  return JSON.stringify(value || {}, null, 2);
}

function createField() {
  return {
    id: "field-" + Date.now() + "-" + Math.random().toString(36).slice(2, 8),
    name: "",
    type: "string",
    required: false,
    description: "",
    example: "",
    itemType: "string",
    arrayLength: 1,
    itemExamples: [],
    itemObjects: [],
    expanded: true,
    children: [],
  };
}

function inferFieldType(value) {
  if (Array.isArray(value)) return "array";
  if (value !== null && typeof value === "object") return "object";
  if (typeof value === "number") return "number";
  if (typeof value === "boolean") return "boolean";
  return "string";
}

function inferItemType(value) {
  if (Array.isArray(value) && value.length > 0) {
    const type = inferFieldType(value[0]);
    return type === "array" ? "string" : type;
  }
  return "string";
}

function buildFieldsFromObject(record) {
  if (!record || typeof record !== "object" || Array.isArray(record)) {
    return [];
  }
  return Object.entries(record).map(([key, value]) => buildFieldFromValue(key, value));
}

function buildFieldFromValue(name, value) {
  const type = inferFieldType(value);
  const field = { ...createField(), name, type };

  if (type === "object") {
    field.children = buildFieldsFromObject(value);
    return field;
  }

  if (type === "array") {
    field.itemType = inferItemType(value);
    field.arrayLength = Math.max(value.length, 1);
    if (field.itemType === "object" && value.length > 0) {
      field.itemObjects = value.filter((item) => item && typeof item === "object" && !Array.isArray(item));
      field.children = buildFieldsFromArrayObjects(field.itemObjects);
    } else if (value.length > 0 && value[0] !== null && typeof value[0] !== "object") {
      field.example = String(value[0]);
      field.itemExamples = value.map((item) => (item === null || item === undefined ? "" : String(item)));
    }
    return field;
  }

  if (value !== null && value !== undefined) {
    field.example = String(value);
  }
  return field;
}

function buildFieldsFromArrayObjects(records) {
  if (!Array.isArray(records) || !records.length) {
    return [];
  }
  const keys = Array.from(new Set(records.flatMap((record) => Object.keys(record || {}))));
  return keys.map((key) => {
    const values = records.map((record) => record?.[key]);
    const firstValue = values.find((value) => value !== undefined);
    const field = buildFieldFromValue(key, firstValue);
    if (field.type === "object") {
      field.children = buildFieldsFromArrayObjects(
        values.filter((value) => value && typeof value === "object" && !Array.isArray(value)),
      );
    } else if (field.type !== "array") {
      field.itemExamples = values.map((value) => (value === null || value === undefined ? "" : String(value)));
    }
    return field;
  });
}

function canHaveChildren(field) {
  return field.type === "object" || (field.type === "array" && field.itemType === "object");
}

function previewValue(field, itemIndex = null) {
  if (field.type === "object") {
    return previewObjectFromFields(field.children, itemIndex);
  }
  if (field.type === "array") {
    const length = Math.max(Number(field.arrayLength || 1), 1);
    if (field.itemType === "object") {
      return Array.from({ length }, (_, index) => previewObjectFromFields(field.children, index));
    }
    if (field.itemType === "number") return previewPrimitiveArray(field, (value) => Number(value || 0));
    if (field.itemType === "boolean") return previewPrimitiveArray(field, (value) => value === "true");
    return previewPrimitiveArray(field, (value) => value || "");
  }
  if (field.type === "number") return Number(exampleForIndex(field, itemIndex) || 0);
  if (field.type === "boolean") return exampleForIndex(field, itemIndex) === "true";
  return exampleForIndex(field, itemIndex) || "";
}

function previewObjectFromFields(nodes, itemIndex = null) {
  return Object.fromEntries(nodes.map((child) => [child.name || "field", previewValue(child, itemIndex)]));
}

function exampleForIndex(field, itemIndex) {
  if (itemIndex !== null && field.itemExamples?.length) {
    return field.itemExamples[itemIndex] ?? field.example;
  }
  return field.example;
}

function previewPrimitiveArray(field, normalize) {
  const examples = field.itemExamples?.length ? field.itemExamples : [field.example];
  if (examples.length && field.example !== "" && field.example !== examples[0]) {
    return Array.from({ length: examples.length }, () => normalize(field.example));
  }
  return examples.map((value) => normalize(value));
}

function validateFields(nodes, path = "root") {
  for (const field of nodes) {
    if (!field.name.trim()) {
      throw new Error("Missing field name at " + path);
    }
    if (canHaveChildren(field)) {
      validateFields(field.children, path + "." + field.name);
    }
  }
}

onMounted(() => window.addEventListener("keydown", handleSaveShortcut));
onBeforeUnmount(() => window.removeEventListener("keydown", handleSaveShortcut));
</script>
