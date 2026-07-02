<template>
  <div ref="containerRef" class="file-filter-menu">
    <button
      class="file-filter-trigger ui-btn ui-btn-secondary"
      type="button"
      :class="{ active: hasActiveFilters || open }"
      :aria-expanded="open"
      aria-haspopup="dialog"
      @click="toggleOpen"
    >
      <svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 5h16l-6 7v5l-4 2v-7L4 5Z" fill="currentColor" />
      </svg>
      <span>{{ isFiltering ? "Filtering..." : "Filter" }}</span>
      <span v-if="hasActiveFilters" class="file-filter-trigger-count">{{ selectedCount }}</span>
    </button>

    <div v-if="open" class="file-filter-popover ui-popover ui-panel" role="dialog" aria-label="File filter">
      <div class="file-filter-popover-header ui-panel-header">
        <div>
          <p class="eyebrow">Explorer Filter</p>
          <h3>Filter File Tree</h3>
        </div>
        <button class="ui-action-close ui-icon-close ui-btn ui-icon-btn" type="button" aria-label="Close filter" @click="closeOpen">
          <svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M6 6 18 18M18 6 6 18"
              fill="none"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-width="2"
            />
          </svg>
        </button>
      </div>

      <label class="file-filter-search ui-field">
        <span>Name Filter</span>
        <input
          v-model.trim="draftQuery"
          class="file-filter-search-input"
          type="search"
          placeholder="Filter files or folders"
          aria-label="Filter files or folders"
          @keydown.enter.prevent="emitApply"
        />
      </label>

      <div class="file-filter-groups ui-list">
        <section v-for="group in extensionGroups" :key="group.id" class="file-filter-group ui-card">
          <div class="file-filter-group-header">
            <label class="file-filter-checkbox emphasis">
              <input
                :checked="isGroupChecked(group.extensions)"
                type="checkbox"
                @change="toggleGroup(group.extensions, $event.target.checked)"
              />
              <span>{{ group.label }}</span>
            </label>
            <span class="file-filter-group-count">{{ countSelectedInGroup(group.extensions) }}/{{ group.extensions.length }}</span>
          </div>

          <div class="file-filter-extension-list">
            <label v-for="extension in group.extensions" :key="extension" class="file-filter-checkbox">
              <input
                :checked="draftExtensionSet.has(extension)"
                type="checkbox"
                @change="toggleExtension(extension, $event.target.checked)"
              />
              <span>{{ extension }}</span>
            </label>
          </div>
        </section>
      </div>

      <footer class="file-filter-actions ui-footer-actions">
        <button class="ui-btn" type="button" :disabled="!hasDraftFilters" @click="resetDraft">
          Clear
        </button>
        <button class="ui-btn ui-btn-primary" type="button" :disabled="isFiltering" @click="emitApply">
          Apply
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
  query: { type: String, default: "" },
  extensions: { type: Array, default: () => [] },
  extensionGroups: {
    type: Array,
    default: () => [
      { id: "images", label: "Images", extensions: [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".svg"] },
      { id: "videos", label: "Videos", extensions: [".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v"] },
      { id: "archives", label: "Archives", extensions: [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tgz"] },
      { id: "audio", label: "Audio", extensions: [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"] },
    ],
  },
  isFiltering: { type: Boolean, default: false },
});

const emit = defineEmits(["apply"]);
const containerRef = ref(null);
const open = ref(false);
const draftQuery = ref(props.query);
const draftExtensions = ref([...props.extensions]);
const draftExtensionSet = computed(() => new Set(draftExtensions.value));
const hasActiveFilters = computed(() => Boolean(props.query.trim()) || props.extensions.length > 0);
const hasDraftFilters = computed(() => Boolean(draftQuery.value.trim()) || draftExtensions.value.length > 0);
const selectedCount = computed(() => (props.query.trim() ? 1 : 0) + props.extensions.length);

watch(() => [props.query, props.extensions], () => { if (!open.value) syncDraftFromProps(); }, { deep: true });
function syncDraftFromProps() { draftQuery.value = props.query; draftExtensions.value = [...props.extensions]; }
function toggleOpen() { if (!open.value) syncDraftFromProps(); open.value = !open.value; }
function closeOpen() { open.value = false; }
function normalizeExtensions(list) { return Array.from(new Set(list)).sort(); }
function toggleExtension(extension, checked) { const next = new Set(draftExtensions.value); checked ? next.add(extension) : next.delete(extension); draftExtensions.value = normalizeExtensions(Array.from(next)); }
function toggleGroup(extensions, checked) { const next = new Set(draftExtensions.value); for (const extension of extensions) checked ? next.add(extension) : next.delete(extension); draftExtensions.value = normalizeExtensions(Array.from(next)); }
function isGroupChecked(extensions) { return extensions.every((extension) => draftExtensionSet.value.has(extension)); }
function countSelectedInGroup(extensions) { return extensions.filter((extension) => draftExtensionSet.value.has(extension)).length; }
function resetDraft() { draftQuery.value = ""; draftExtensions.value = []; emitApply(); }
function emitApply() { emit("apply", { query: draftQuery.value.trim(), extensions: normalizeExtensions(draftExtensions.value) }); closeOpen(); }
function handlePointerDown(event) { if (!open.value) return; const container = containerRef.value; if (container && !container.contains(event.target)) closeOpen(); }
onMounted(() => window.addEventListener("pointerdown", handlePointerDown, true));
onBeforeUnmount(() => window.removeEventListener("pointerdown", handlePointerDown, true));
</script>
