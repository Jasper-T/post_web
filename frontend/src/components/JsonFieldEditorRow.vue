<template>
  <div class="json-field-group ui-list">
    <article v-for="(field, index) in fields" :key="field.id" class="json-field-card ui-card">
      <div class="json-field-card-header ui-panel-header">
        <div class="json-field-card-title">
          <button class="json-field-collapse ui-icon-collapse ui-icon-btn" type="button" @click="field.expanded = field.expanded === false">
            {{ field.expanded === false ? "+" : "-" }}
          </button>
          <strong>{{ field.name || 'Field ' + (index + 1) }}</strong>
          <span class="json-field-card-tag">{{ labelForField(field) }}</span>
        </div>
        <div class="json-field-card-actions ui-toolbar">
          <button class="ui-btn" type="button" @click="addChild(field)" :disabled="!canHaveChildren(field)">Add Child</button>
          <button class="ui-action-delete ui-icon-delete ui-btn ui-btn-danger" type="button" @click="removeField(index)"><span class="ui-action-label">Delete</span></button>
        </div>
      </div>
      <template v-if="field.expanded !== false">
        <div class="tool-field-row">
          <label class="tool-field ui-field"><span>Name</span><input v-model.trim="field.name" type="text" placeholder="e.g. title / userName" /></label>
          <label class="tool-field ui-field"><span>Type</span><select class="compact-select" v-model="field.type" @change="handleTypeChange(field)"><option value="string">string</option><option value="number">number</option><option value="boolean">boolean</option><option value="object">object</option><option value="array">array</option></select></label>
        </div>
        <div class="tool-field-row">
          <label v-if="field.type === 'array'" class="tool-field ui-field"><span>Array Item Type</span><select class="compact-select" v-model="field.itemType" @change="handleArrayItemTypeChange(field)"><option value="string">string</option><option value="number">number</option><option value="boolean">boolean</option><option value="object">object</option></select></label>
          <label class="tool-field ui-field"><span>Example</span><input v-model="field.example" type="text" :placeholder="field.type === 'array' ? 'Array item example, optional' : 'hello / 1 / true'" :disabled="usesChildren(field)" /></label>
        </div>
        <div class="tool-field-row">
          <label class="tool-field ui-field"><span>Description</span><input v-model.trim="field.description" type="text" placeholder="Optional description" /></label>
          <label class="json-field-checkbox"><input v-model="field.required" type="checkbox" /><span>Required Field</span></label>
        </div>
        <div v-if="canHaveChildren(field)" class="json-field-children">
          <div class="json-field-children-header"><span>Children</span><button class="ui-btn" type="button" @click="addChild(field)">Add Child</button></div>
          <JsonFieldEditorRow :fields="field.children" />
        </div>
      </template>
    </article>
  </div>
</template>

<script setup>
defineOptions({ name: "JsonFieldEditorRow" });
const props = defineProps({ fields: { type: Array, required: true } });
function createField() { return { id: "field-" + Date.now() + "-" + Math.random().toString(36).slice(2, 8), name: "", type: "string", required: false, description: "", example: "", itemType: "string", arrayLength: 1, itemExamples: [], itemObjects: [], expanded: true, children: [] }; }
function canHaveChildren(field) { return field.type === "object" || (field.type === "array" && field.itemType === "object"); }
function usesChildren(field) { return canHaveChildren(field); }
function handleTypeChange(field) { if (field.type === "array") { field.itemType = field.itemType || "string"; field.arrayLength = field.arrayLength || 1; field.itemExamples = field.itemExamples || []; if (field.itemType !== "object") field.children = []; else if (!field.children.length) field.children.push(createField()); return; } field.itemType = "string"; if (field.type !== "object") field.children = []; else if (!field.children.length) field.children.push(createField()); }
function handleArrayItemTypeChange(field) { if (field.itemType === "object") { if (!field.children.length) field.children.push(createField()); return; } field.children = []; }
function addChild(field) { if (!canHaveChildren(field)) return; field.children.push(createField()); field.expanded = true; }
function removeField(index) { props.fields.splice(index, 1); }
function labelForField(field) { return field.type === "array" ? "array<" + (field.itemType || "string") + ">" : field.type; }
</script>
