<template>
  <section class="panel panel-list-layout">
    <header class="panel-header">
      <div>
        <p class="eyebrow">{{ eyebrow }}</p>
        <h2>{{ title }}</h2>
      </div>
      <span v-if="summary" class="selected-summary">{{ summary }}</span>
    </header>

    <div v-if="$slots.toolbar" class="selected-toolbar">
      <slot name="toolbar" />
    </div>

    <div class="panel-list-body">
      <slot />
    </div>
  </section>
</template>

<script setup>
defineProps({
  eyebrow: {
    type: String,
    default: "List",
  },
  title: {
    type: String,
    default: "Items",
  },
  summary: {
    type: String,
    default: "",
  },
});
</script>
