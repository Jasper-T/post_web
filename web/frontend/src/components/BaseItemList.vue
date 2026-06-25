<template>
  <div v-if="items.length === 0" class="empty-state multiline-empty-state">
    <span>{{ emptyMessage }}</span>
  </div>

  <ul v-else ref="listRef" class="base-item-list">
    <li
      v-for="(item, index) in items"
      :key="itemValue(item)"
      class="base-item-row"
      :class="{ active: activeValue === itemValue(item) }"
      :data-item-value="itemValue(item)"
      @click="$emit('select', item)"
      @dblclick="$emit('open', item)"
    >
      <slot
        name="item"
        :item="item"
        :index="index"
        :is-active="activeValue === itemValue(item)"
        :value="itemValue(item)"
        :text="itemText(item)"
      >
        <div class="base-item-text">{{ itemText(item) }}</div>
      </slot>
    </li>
  </ul>
</template>

<script setup>
import { nextTick, ref, watch } from "vue";

const props = defineProps({
  items: {
    type: Array,
    required: true,
  },
  activeValue: {
    type: String,
    default: "",
  },
  emptyMessage: {
    type: String,
    default: "No items.",
  },
  valueKey: {
    type: String,
    default: "value",
  },
  textKey: {
    type: String,
    default: "label",
  },
  autoScrollActive: {
    type: Boolean,
    default: true,
  },
});

defineEmits(["select", "open"]);

const listRef = ref(null);

function itemValue(item) {
  return String(item?.[props.valueKey] ?? "");
}

function itemText(item) {
  return String(item?.[props.textKey] ?? itemValue(item));
}

function escapeSelector(value) {
  if (globalThis.CSS?.escape) {
    return globalThis.CSS.escape(value);
  }

  return value.replace(/["\\]/g, "\\$&");
}

async function scrollActiveIntoView() {
  if (!props.autoScrollActive || !props.activeValue) {
    return;
  }

  await nextTick();
  const container = listRef.value;
  if (!container) {
    return;
  }

  const target = container.querySelector(`[data-item-value="${escapeSelector(props.activeValue)}"]`);
  if (!target) {
    return;
  }

  target.scrollIntoView({
    block: "nearest",
    inline: "nearest",
  });
}

watch(
  () => props.activeValue,
  () => {
    scrollActiveIntoView();
  },
);

watch(
  () => props.items.length,
  () => {
    scrollActiveIntoView();
  },
);
</script>
