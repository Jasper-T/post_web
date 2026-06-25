<template>
  <BaseItemList
    :items="items"
    :active-value="activeValue"
    :empty-message="emptyMessage"
    :value-key="valueKey"
    :text-key="textKey"
    @select="$emit('select', $event)"
    @open="$emit('open', $event)"
  >
    <template #item="{ isActive, text }">
      <div class="readonly-item-row" :class="{ active: isActive }">
        <div class="readonly-item-scroll">
          <span class="readonly-item-text" :title="text">{{ text }}</span>
        </div>
      </div>
    </template>
  </BaseItemList>
</template>

<script setup>
import BaseItemList from "./BaseItemList.vue";

defineProps({
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
});

defineEmits(["select", "open"]);
</script>
