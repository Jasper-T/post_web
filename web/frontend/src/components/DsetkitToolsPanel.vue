<template>
  <div class="tools-panel">
    <section class="tool-context">
      <p class="tool-context-label">当前上下文</p>
      <div class="tool-context-path">{{ currentPath || "暂无选中路径" }}</div>
    </section>

    <div class="tool-tabs" role="tablist" aria-label="dsetkit tools">
      <button
        v-for="tool in tools"
        :key="tool.id"
        class="tool-tab"
        type="button"
        :disabled="running"
        role="tab"
        :aria-selected="selectedToolId === tool.id"
        :class="{ active: selectedToolId === tool.id }"
        @click="selectedToolId = tool.id"
      >
        {{ tool.name }}
      </button>
    </div>

    <form class="tool-form tool-tab-panel" role="tabpanel" @submit.prevent="runTool">
      <fieldset class="tool-form-body" :disabled="running">
      <div class="tool-panel-intro">
        <p>{{ selectedTool?.description }}</p>
      </div>

      <label class="tool-field">
        <span>图像目录</span>
        <div class="tool-path-input">
          <input v-model.trim="form.imageDir" type="text" placeholder="/path/to/images" />
          <button class="small-button" type="button" :disabled="!currentPath || running" @click="fillPath('imageDir')">
            填入当前
          </button>
        </div>
      </label>

      <label class="tool-field">
        <span>标签目录</span>
        <div class="tool-path-input">
          <input v-model.trim="form.labelDir" type="text" placeholder="/path/to/labels" />
          <button class="small-button" type="button" :disabled="!currentPath || running" @click="fillPath('labelDir')">
            填入当前
          </button>
        </div>
      </label>

      <div class="tool-format-names-row">
        <div class="tool-format-stack">
          <label class="tool-field">
            <span>源格式</span>
            <select class="compact-select" v-model="form.sourceFormat">
              <option v-for="format in formats" :key="format" :value="format">{{ format }}</option>
            </select>
          </label>

          <label v-if="selectedTool?.requiresTargetFormat" class="tool-field">
            <span>目标格式</span>
            <select class="compact-select" v-model="form.targetFormat">
              <option v-for="format in formats" :key="format" :value="format">{{ format }}</option>
            </select>
          </label>
        </div>

        <label class="tool-field">
          <span>类别名</span>
          <textarea
            v-model="form.names"
            rows="5"
            placeholder="每行一个类别，例如：&#10;cat&#10;dog&#10;&#10;或用逗号分隔，例如：cat,dog"
          ></textarea>
        </label>
      </div>

      <label class="tool-field">
        <span>输出目录</span>
        <div class="tool-path-input">
          <input v-model.trim="form.outDir" type="text" placeholder="留空使用标签文件夹的同级目录" />
          <button class="small-button" type="button" :disabled="!currentPath || running" @click="fillPath('outDir')">
            填入当前
          </button>
        </div>
      </label>

      <div v-if="toolsError" class="tool-alert error">{{ toolsError }}</div>
      <div v-if="runError" class="tool-alert error">{{ runError }}</div>
      <div v-if="result" class="tool-alert success">
        <strong>{{ result.message }}</strong>
        <span v-if="result.outputDir">输出目录：{{ result.outputDir }}</span>
      </div>

      <footer class="tool-form-actions">
        <button class="small-button" type="button" @click="resetForm">重置</button>
        <button class="small-button primary-button" type="submit" :disabled="!canRun || running">
          {{ running ? "执行中..." : "执行工具" }}
        </button>
      </footer>
      </fieldset>
    </form>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";

const props = defineProps({
  activeWorkflowPath: {
    type: String,
    default: "",
  },
  workflowTreeSelectedPath: {
    type: String,
    default: "",
  },
});

const fallbackFormats = ["labelme", "voc", "yolo"];
const fallbackTools = [
  {
    id: "convert",
    name: "标注格式转换",
    description: "批量转换 LabelMe / VOC / YOLO 标注格式。",
    requiresTargetFormat: true,
  },
  {
    id: "plot",
    name: "标注可视化",
    description: "把标注框绘制到图像上并批量导出。",
    requiresTargetFormat: false,
  },
];

const formats = ref(fallbackFormats);
const tools = ref(fallbackTools);
const selectedToolId = ref("convert");
const running = ref(false);
const toolsError = ref("");
const runError = ref("");
const result = ref(null);

const form = reactive(createInitialForm());

const currentPath = computed(() => {
  return props.workflowTreeSelectedPath || props.activeWorkflowPath;
});

const selectedTool = computed(() => {
  return tools.value.find((tool) => tool.id === selectedToolId.value);
});

const canRun = computed(() => {
  const hasNames = normalizeNames(form.names).length > 0;
  const hasTarget = !selectedTool.value?.requiresTargetFormat || Boolean(form.targetFormat);
  return Boolean(form.imageDir && form.labelDir && form.sourceFormat && hasTarget && hasNames);
});

function createInitialForm(path = "") {
  return {
    imageDir: path,
    labelDir: "",
    sourceFormat: "labelme",
    targetFormat: "yolo",
    names: "",
    outDir: "",
  };
}

function normalizeNames(value) {
  return value
    .replaceAll(",", "\n")
    .split("\n")
    .map((name) => name.trim())
    .filter(Boolean);
}

function fillPath(field) {
  if (currentPath.value) {
    form[field] = currentPath.value;
  }
}

function resetForm() {
  Object.assign(form, createInitialForm(currentPath.value));
  runError.value = "";
  result.value = null;
}

function endpointForSelectedTool() {
  return selectedToolId.value === "plot" ? "/api/dsetkit/plot" : "/api/dsetkit/convert";
}

function buildPayload() {
  const payload = {
    imageDir: form.imageDir,
    labelDir: form.labelDir,
    sourceFormat: form.sourceFormat,
    names: normalizeNames(form.names),
    outDir: form.outDir || null,
  };

  if (selectedTool.value?.requiresTargetFormat) {
    payload.targetFormat = form.targetFormat;
  }

  return payload;
}

async function fetchTools() {
  toolsError.value = "";

  try {
    const response = await fetch("/api/dsetkit/tools");
    if (!response.ok) {
      throw await responseToError(response, "读取 dsetkit 工具失败");
    }

    const data = await response.json();
    formats.value = data.formats?.length ? data.formats : fallbackFormats;
    tools.value = data.tools?.length ? data.tools : fallbackTools;
  } catch (error) {
    toolsError.value = error.message;
  }
}

async function runTool() {
  if (!canRun.value || running.value) {
    return;
  }

  running.value = true;
  runError.value = "";
  result.value = null;

  try {
    const response = await fetch(endpointForSelectedTool(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(buildPayload()),
    });

    if (!response.ok) {
      throw await responseToError(response, "dsetkit 工具执行失败");
    }

    result.value = await response.json();
  } catch (error) {
    runError.value = error.message;
  } finally {
    running.value = false;
  }
}

async function responseToError(response, fallback) {
  const data = await response.json().catch(() => ({}));
  const detail = Array.isArray(data.detail)
    ? data.detail.map((item) => item.msg || JSON.stringify(item)).join("; ")
    : data.detail;
  return new Error(detail || `${fallback}: ${response.status}`);
}

watch(
  currentPath,
  (path) => {
    if (path && !form.imageDir) {
      form.imageDir = path;
    }
  },
  { immediate: true },
);

watch(selectedToolId, () => {
  runError.value = "";
  result.value = null;
});

onMounted(fetchTools);
</script>
