<template>
  <div class="kv-editor">
    <div class="kv-editor-table">
      <div class="kv-editor-head">
        <span class="kv-col-check">Use</span>
        <span class="kv-col-name">Name</span>
        <span class="kv-col-value">{{ valueLabel }}</span>
        <span class="kv-col-type">Type</span>
        <span class="kv-col-actions"></span>
      </div>

      <div v-for="(row, index) in rows" :key="row.id" class="kv-editor-row">
        <label class="kv-col-check kv-check-cell">
          <input
            :checked="row.enabled"
            type="checkbox"
            @change="updateRow(index, 'enabled', $event.target.checked)"
          />
        </label>

        <input
          class="kv-cell-input kv-col-name"
          :value="row.name"
          placeholder="field.name"
          @input="updateRow(index, 'name', $event.target.value)"
        />

        <select
          v-if="hasValueOptions"
          class="kv-cell-input kv-col-value"
          :value="row.value"
          @change="updateRow(index, 'value', $event.target.value)"
        >
          <option value="">请选择</option>
          <option v-for="option in valueOptions" :key="option" :value="option">
            {{ option }}
          </option>
        </select>

        <input
          v-else
          class="kv-cell-input kv-col-value"
          :value="row.value"
          placeholder="value"
          @input="updateRow(index, 'value', $event.target.value)"
        />

        <select
          class="kv-cell-input kv-col-type"
          :value="row.type"
          @change="updateRow(index, 'type', $event.target.value)"
        >
          <option value="string">string</option>
          <option value="number">number</option>
          <option value="boolean">boolean</option>
          <option value="null">null</option>
          <option value="json">json</option>
        </select>

        <button class="kv-delete-button" type="button" @click="removeRow(index)">
          Delete
        </button>
      </div>
    </div>

    <div class="kv-editor-actions">
      <button class="small-button" type="button" @click="openBulkEdit">Bulk Edit</button>
      <button class="small-button" type="button" @click="addRow">Add Row</button>
    </div>

    <div v-if="showBulkEdit" class="kv-bulk-backdrop" @click.self="closeBulkEdit">
      <div class="kv-bulk-dialog">
        <div class="kv-bulk-header">
          <div>
            <h4>Bulk Edit</h4>
            <p>每行一条，格式：enabled[TAB]name[TAB]value[TAB]type</p>
          </div>
          <button class="small-button icon-button" type="button" title="关闭" aria-label="关闭批量编辑弹窗" @click="closeBulkEdit"><svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg></button>
        </div>

        <textarea
          v-model="bulkText"
          class="kv-bulk-textarea"
          rows="14"
          spellcheck="false"
        ></textarea>

        <div v-if="bulkError" class="tool-alert error">{{ bulkError }}</div>

        <div class="kv-editor-actions">
          <button class="small-button" type="button" @click="fillBulkSample">示例</button>
          <button class="small-button primary-button" type="button" @click="applyBulkEdit">应用</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  rows: {
    type: Array,
    default: () => [],
  },
  valueOptions: {
    type: Array,
    default: () => [],
  },
  valueLabel: {
    type: String,
    default: "Value",
  },
});

const emit = defineEmits(["update:rows"]);

const showBulkEdit = ref(false);
const bulkText = ref("");
const bulkError = ref("");

const hasValueOptions = computed(() => props.valueOptions.length > 0);

function updateRow(index, key, value) {
  const nextRows = props.rows.map((row, rowIndex) =>
    rowIndex === index ? { ...row, [key]: value } : row
  );
  emit("update:rows", nextRows);
}

function addRow() {
  emit("update:rows", [
    ...props.rows,
    {
      id: `row-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      enabled: true,
      name: "",
      value: "",
      type: "string",
    },
  ]);
}

function removeRow(index) {
  emit(
    "update:rows",
    props.rows.filter((_, rowIndex) => rowIndex !== index)
  );
}

function openBulkEdit() {
  bulkError.value = "";
  bulkText.value = props.rows
    .map((row) => [row.enabled ? "true" : "false", row.name, row.value, row.type].join("\t"))
    .join("\n");
  showBulkEdit.value = true;
}

function closeBulkEdit() {
  showBulkEdit.value = false;
  bulkError.value = "";
}

function fillBulkSample() {
  bulkText.value =
    "true\tContent-Type\tapplication/json\tstring\ntrue\tAuthorization\tBearer {{OPENAI_API_KEY}}\tstring";
}

function applyBulkEdit() {
  try {
    const nextRows = bulkText.value
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line, index) => {
        const parts = line.split("\t");
        if (parts.length < 4) {
          throw new Error(`第 ${index + 1} 行格式不对，至少需要 4 列`);
        }

        const [enabledRaw, name, ...rest] = parts;
        const type = rest.pop();
        const value = rest.join("\t");
        return {
          id: `row-${Date.now()}-${index}-${Math.random().toString(36).slice(2, 8)}`,
          enabled: enabledRaw !== "false",
          name,
          value,
          type: type || "string",
        };
      });

    emit(
      "update:rows",
      nextRows.length
        ? nextRows
        : [
            {
              id: `row-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
              enabled: true,
              name: "",
              value: "",
              type: "string",
            },
          ]
    );
    closeBulkEdit();
  } catch (error) {
    bulkError.value = error.message || "Bulk Edit 解析失败";
  }
}
</script>
