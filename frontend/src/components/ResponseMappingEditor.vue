<template>
  <div class="mapping-editor">
    <div class="template-editor-toolbar ui-toolbar">
      <span class="template-editor-title">Parsing</span>
      <div class="json-template-actions ui-toolbar">
        <button class="ui-btn ui-btn-primary" type="button" @click="$emit('save')">Save</button>
        <button class="ui-btn" type="button" @click="showPreview = true">Preview</button>
      </div>
    </div>

    <label class="tool-field ui-field">
      <span>Collection Path</span>
      <select
        class="kv-cell-input"
        :value="modelValue.collectionPath"
        @change="updateField('collectionPath', $event.target.value)"
      >
        <option value="">None</option>
        <option v-for="path in collectionPathOptions" :key="`collection-${path}`" :value="path">
          {{ path }}
        </option>
      </select>
    </label>

    <label class="tool-field ui-field">
      <span>Item Path</span>
      <select class="kv-cell-input" :value="modelValue.itemPath" @change="updateField('itemPath', $event.target.value)">
        <option value="">None</option>
        <option v-for="path in itemPathOptions" :key="`item-${path}`" :value="path">
          {{ path }}
        </option>
      </select>
    </label>

    <div class="mapping-switch-row">
      <div class="mapping-switch ui-switch-card">
        <span>BBox / Point</span>
        <strong>{{ modelValue.bboxInputMode === "fields" ? "Point" : "BBox" }}</strong>
        <button
          class="mapping-switch-button ui-icon-switch ui-icon-btn"
          type="button"
          :title="modelValue.bboxInputMode === 'fields' ? 'Switch to BBox' : 'Switch to Point'"
          :aria-label="modelValue.bboxInputMode === 'fields' ? 'Switch to BBox' : 'Switch to Point'"
          @click="toggleBBoxInputMode"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M7 7h11l-3-3M17 17H6l3 3" />
            <path d="M18 7l-3 3M6 17l3-3" />
          </svg>
        </button>
      </div>
      <div class="mapping-switch ui-switch-card">
        <span>XYWH / XYXY</span>
        <strong>{{ modelValue.bboxCoordinateType === "xywh" ? "XYWH" : "XYXY" }}</strong>
        <button
          class="mapping-switch-button ui-icon-switch ui-icon-btn"
          type="button"
          :title="modelValue.bboxCoordinateType === 'xywh' ? 'Switch to XYXY' : 'Switch to XYWH'"
          :aria-label="modelValue.bboxCoordinateType === 'xywh' ? 'Switch to XYXY' : 'Switch to XYWH'"
          @click="toggleBBoxCoordinateType"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M7 7h11l-3-3M17 17H6l3 3" />
            <path d="M18 7l-3 3M6 17l3-3" />
          </svg>
        </button>
      </div>
    </div>

    <div class="mapping-table ui-table">
      <div class="mapping-head mapping-head-compact">
        <span>Key(out)</span>
        <span>Type</span>
        <span>Source Path</span>
        <span>Plot</span>
      </div>

      <div v-for="(row, index) in detectionRows" :key="`det-${row.key}`" class="mapping-row mapping-row-compact ui-table-row">
        <input class="kv-cell-input" :value="row.key" disabled />
        <input class="kv-cell-input" :value="row.type" disabled />
        <select
          class="kv-cell-input"
          :value="row.path"
          @change="updateDetectionPath(index, $event.target.value)"
        >
          <option value="">None</option>
          <option v-for="path in sourcePathOptions" :key="`det-${row.key}-${path}`" :value="path">
            {{ path }}
          </option>
        </select>
        <label v-if="!row.isBBox" class="mapping-plot-check" :title="'Use ' + row.key + ' in plot text'">
          <input type="checkbox" :checked="isPlotField(row.key)" @change="togglePlotField(row.key, $event.target.checked)" />
        </label>
        <span v-else class="mapping-plot-unavailable">-</span>
      </div>
    </div>

    <div class="mapping-extra-header ui-toolbar">
      <span class="template-editor-title">Extra Params</span>
      <button class="ui-btn" type="button" @click="addExtraRow">Add</button>
    </div>

    <div class="mapping-table ui-table">
      <div class="mapping-head mapping-head-compact">
        <span>Key(out)</span>
        <span>Type</span>
        <span>Source Path</span>
        <span>Plot</span>
        <span></span>
      </div>

      <div v-for="(row, index) in modelValue.extraFields" :key="row.id" class="mapping-row mapping-row-extra ui-table-row">
        <input class="kv-cell-input" :value="row.name" @input="updateExtraRow(index, 'name', $event.target.value)" />
        <select class="kv-cell-input" :value="row.cast" @change="updateExtraRow(index, 'cast', $event.target.value)">
          <option value="string">string</option>
          <option value="int">int</option>
          <option value="float">float</option>
          <option value="bool">bool</option>
        </select>
        <select class="kv-cell-input" :value="row.path" @change="updateExtraRow(index, 'path', $event.target.value)">
          <option value="">None</option>
          <option v-for="path in sourcePathOptions" :key="`extra-${index}-${path}`" :value="path">
            {{ path }}
          </option>
        </select>
        <label class="mapping-plot-check" :title="row.name ? 'Use ' + row.name + ' in plot text' : 'Set Key(out) first'">
          <input type="checkbox" :checked="Boolean(row.plot)" :disabled="!String(row.name || '').trim()" @change="updateExtraPlot(index, $event.target.checked)" />
        </label>
        <button class="ui-action-delete ui-icon-delete kv-delete-button ui-btn ui-btn-danger" type="button" @click="removeExtraRow(index)"><span class="ui-action-label">Delete</span></button>
      </div>
    </div>

    <div v-if="showPreview" class="json-import-backdrop" @click.self="showPreview = false">
      <div class="json-import-dialog json-preview-dialog ui-panel">
        <div class="json-import-dialog-header ui-panel-header">
          <h4>Schema Preview</h4>
          <button class="ui-action-close ui-icon-close ui-btn ui-icon-btn" type="button" title="Close" aria-label="Close schema preview" @click="showPreview = false"><svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg></button>
        </div>
        <pre class="json-template-saved-preview">{{ previewText }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  modelValue: { type: Object, required: true },
  sourcePathOptions: { type: Array, default: () => [] },
  collectionPathOptions: { type: Array, default: () => [] },
  itemPathOptions: { type: Array, default: () => [] },
});

const emit = defineEmits(["update:modelValue", "save", "read"]);

const showPreview = ref(false);

const detectionRows = computed(() => {
  const common = [
    { key: "label", path: props.modelValue.labelPath || "", type: "string", isBBox: false },
    { key: "class_id", path: props.modelValue.classIdPath || "", type: "int", isBBox: false },
    { key: "conf", path: props.modelValue.confPath || "", type: "float", isBBox: false },
  ];

  if (props.modelValue.bboxInputMode === "fields") {
    const labels = props.modelValue.bboxCoordinateType === "xywh" ? ["x", "y", "w", "h"] : ["x1", "y1", "x2", "y2"];
    return labels.map((key, index) => ({
      key,
      path: props.modelValue.bboxPaths?.[index] || "",
      type: "float",
      isBBox: true,
    })).concat(common);
  }

  return [{ key: "bbox", path: props.modelValue.bboxPath || "", type: "float[]", isBBox: true }, ...common];
});

const previewText = computed(() => JSON.stringify(buildSchemaPreview(props.modelValue), null, 2));

function cloneValue() {
  return {
    ...props.modelValue,
    bboxPaths: [...(props.modelValue.bboxPaths || [null, null, null, null])],
    plotFields: [...(props.modelValue.plotFields || [])],
    extraFields: (props.modelValue.extraFields || []).map((field) => ({ ...field })),
  };
}

function toggleBBoxInputMode() {
  updateField("bboxInputMode", props.modelValue.bboxInputMode === "fields" ? "list" : "fields");
}

function toggleBBoxCoordinateType() {
  updateField("bboxCoordinateType", props.modelValue.bboxCoordinateType === "xywh" ? "xyxy" : "xywh");
}

function updateField(key, value) {
  emit("update:modelValue", { ...cloneValue(), [key]: value });
}

function updateDetectionPath(index, value) {
  const nextValue = cloneValue();
  const bboxRows = nextValue.bboxInputMode === "fields" ? 4 : 1;
  if (nextValue.bboxInputMode === "fields" && index < 4) {
    nextValue.bboxPaths[index] = value || null;
  } else if (nextValue.bboxInputMode === "list" && index === 0) {
    nextValue.bboxPath = value || null;
  } else {
    const key = detectionRows.value[index]?.key;
    if (key === "label") {
      nextValue.labelPath = value || null;
    }
    if (key === "class_id") {
      nextValue.classIdPath = value || null;
    }
    if (key === "conf") {
      nextValue.confPath = value || null;
    }
  }
  if (nextValue.bboxInputMode === "fields" && index >= bboxRows) {
    const key = detectionRows.value[index]?.key;
    if (key === "label") {
      nextValue.labelPath = value || null;
    }
    if (key === "class_id") {
      nextValue.classIdPath = value || null;
    }
    if (key === "conf") {
      nextValue.confPath = value || null;
    }
  }
  emit("update:modelValue", nextValue);
}

function addExtraRow() {
  const nextValue = cloneValue();
  nextValue.extraFields.push({
    id: `extra-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    name: "",
    path: "",
    cast: "string",
    plot: false,
  });
  emit("update:modelValue", nextValue);
}

function updateExtraRow(index, key, value) {
  const nextValue = cloneValue();
  nextValue.extraFields = nextValue.extraFields.map((row, rowIndex) => {
    if (rowIndex !== index) return row;
    const nextRow = { ...row, [key]: value };
    if (key === "name" && row.plot) {
      nextValue.plotFields = nextValue.plotFields.filter((field) => field !== row.name);
      const normalizedName = String(value || "").trim();
      if (normalizedName) nextValue.plotFields.push(normalizedName);
    }
    return nextRow;
  });
  emit("update:modelValue", nextValue);
}

function isPlotField(key) {
  return (props.modelValue.plotFields || []).includes(key);
}

function togglePlotField(key, checked) {
  const nextValue = cloneValue();
  nextValue.plotFields = nextValue.plotFields.filter((field) => field !== key);
  if (checked) nextValue.plotFields.push(key);
  emit("update:modelValue", nextValue);
}

function updateExtraPlot(index, checked) {
  const nextValue = cloneValue();
  const row = nextValue.extraFields[index];
  if (!row) return;
  const name = String(row.name || "").trim();
  nextValue.extraFields[index] = { ...row, plot: checked };
  nextValue.plotFields = nextValue.plotFields.filter((field) => field !== name);
  if (checked && name) nextValue.plotFields.push(name);
  emit("update:modelValue", nextValue);
}

function removeExtraRow(index) {
  const nextValue = cloneValue();
  const removedName = String(nextValue.extraFields[index]?.name || "").trim();
  nextValue.extraFields = nextValue.extraFields.filter((_, rowIndex) => rowIndex !== index);
  nextValue.plotFields = nextValue.plotFields.filter((field) => field !== removedName);
  emit("update:modelValue", nextValue);
}

function buildSchemaPreview(mapping) {
  const preview = {
    bbox: [0.0, 1.0, 2.0, 3.0],
    conf: null,
    label: null,
    class_id: null,
  };
  for (const field of mapping.extraFields || []) {
    const key = String(field.name || "").trim();
    if (!key) {
      continue;
    }
    preview[key] = defaultValueByCast(field.cast);
  }
  return preview;
}

function defaultValueByCast(cast) {
  if (cast === "int") {
    return 0;
  }
  if (cast === "float") {
    return 0.0;
  }
  if (cast === "bool") {
    return false;
  }
  return "";
}
</script>
