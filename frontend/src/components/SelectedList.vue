<template>
  <PanelListLayout
    :eyebrow="eyebrow"
    :title="title"
    :summary="`Checked ${checkedCount} / ${totalCount} ${summaryLabel}`"
  >
    <template v-if="showToolbar" #toolbar>
      <div class="select-all">
        <div class="select-all-control">
          <input
            type="checkbox"
            :checked="allSelected"
            :indeterminate="partiallySelected"
            :disabled="totalCount === 0"
            @change="$emit('toggle-all', $event.target.checked)"
          />
          <span>Select all</span>
        </div>
        <div class="delete-all-control">
          <span>Delete all</span>
          <button
            class="delete-all-button"
            type="button"
            aria-label="Delete all selected items"
            :disabled="totalCount === 0"
            @click="$emit('delete-all')"
          >
            <svg class="delete-item-icon" viewBox="0 0 24 24" aria-hidden="true">
              <path
                d="M9 3h6l1 2h4v2H4V5h4l1-2Zm1 7v8h2v-8h-2Zm4 0v8h2v-8h-2ZM7 8h10l-1 13H8L7 8Z"
                fill="currentColor"
              />
            </svg>
          </button>
        </div>
      </div>
    </template>

    <BaseItemList
      :items="items"
      :active-value="activeValue"
      :empty-message="emptyMessage"
      :value-key="valueKey"
      :text-key="textKey"
      @select="$emit('select', $event)"
    >
      <template #item="{ item, isActive, text }">
        <div class="selected-item-content" :class="{ active: isActive, 'without-delete': !showDeleteButton }">
          <div class="selected-item-check" @click.stop>
            <input
              type="checkbox"
              :checked="item.checked"
              @change="$emit('update-checked', item, $event.target.checked)"
            />
          </div>
          <div class="selected-item-scroll">
            <span class="selected-item-text" :title="text">{{ text }}</span>
          </div>
          <button
            v-if="showDeleteButton"
            class="delete-item-button"
            type="button"
            :aria-label="`Delete ${text}`"
            @click.stop="$emit('delete', item)"
          >
            <svg class="delete-item-icon" viewBox="0 0 24 24" aria-hidden="true">
              <path
                d="M9 3h6l1 2h4v2H4V5h4l1-2Zm1 7v8h2v-8h-2Zm4 0v8h2v-8h-2ZM7 8h10l-1 13H8L7 8Z"
                fill="currentColor"
              />
            </svg>
          </button>
        </div>
      </template>
    </BaseItemList>
  </PanelListLayout>
</template>

<script setup>
import { computed } from "vue";
import BaseItemList from "./BaseItemList.vue";
import PanelListLayout from "./PanelListLayout.vue";

const props = defineProps({
  items: {
    type: Array,
    required: true,
  },
  checkedCount: {
    type: Number,
    required: true,
  },
  totalCount: {
    type: Number,
    required: true,
  },
  activeValue: {
    type: String,
    default: "",
  },
  eyebrow: {
    type: String,
    default: "Selected",
  },
  title: {
    type: String,
    default: "Selected Items",
  },
  summaryLabel: {
    type: String,
    default: "items",
  },
  emptyMessage: {
    type: String,
    default: "No selected items.",
  },
  showToolbar: {
    type: Boolean,
    default: false,
  },
  showDeleteButton: {
    type: Boolean,
    default: true,
  },
  valueKey: {
    type: String,
    default: "path",
  },
  textKey: {
    type: String,
    default: "path",
  },
});

defineEmits(["update-checked", "toggle-all", "delete", "delete-all", "select"]);

const allSelected = computed(() => {
  return props.totalCount > 0 && props.checkedCount === props.totalCount;
});

const partiallySelected = computed(() => {
  return props.checkedCount > 0 && !allSelected.value;
});
</script>
