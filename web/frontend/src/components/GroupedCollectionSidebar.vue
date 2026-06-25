<template>
  <aside class="sidebar-shell sidebar-shell-compact" :class="{ collapsed: isSidebarCollapsed }">
    <header class="sidebar-header">
      <div v-if="!isSidebarCollapsed">
        <p class="eyebrow">{{ eyebrow }}</p>
        <h2>{{ title }}</h2>
      </div>
      <div class="sidebar-header-actions">
        <button v-if="!isSidebarCollapsed" class="small-button" type="button" @click="showManager = true">Edit</button>
        <button
          class="sidebar-collapse-button"
          type="button"
          :aria-label="isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
          @click="toggleSidebar"
        >
          <svg
            v-if="isSidebarCollapsed"
            class="sidebar-collapse-icon"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path d="m9 18 6-6-6-6" />
          </svg>
          <svg v-else class="sidebar-collapse-icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="m15 18-6-6 6-6" />
          </svg>
        </button>
      </div>
    </header>

    <section v-if="!isSidebarCollapsed" class="panel sidebar-panel collection-sidebar-panel">
      <div class="collection-sidebar-scroll">
        <div class="pipeline-template-list">
          <div v-for="group in regularGroups" :key="group.name" class="pipeline-group-section">
            <button
              class="pipeline-group-toggle"
              type="button"
              :aria-expanded="!collapsedGroups[group.name]"
              @click="toggleGroupCollapse(group.name)"
            >
              <span
                class="pipeline-group-arrow"
                :class="{ collapsed: collapsedGroups[group.name] }"
                aria-hidden="true"
              ></span>
              <div class="pipeline-group-title">
                <strong>{{ group.name }}</strong>
                <span>{{ group.items.length }}</span>
              </div>
            </button>

            <div v-if="!collapsedGroups[group.name]" class="pipeline-group-items">
              <button
                v-for="item in group.items"
                :key="item.key"
                class="pipeline-template-button"
                :class="{ active: activeItemKey === item.key }"
                type="button"
                @click="$emit('select-item', item.raw)"
              >
                <div class="pipeline-template-row">
                  <strong>{{ item.label }}</strong>
                  <span v-if="item.badge" class="request-method-pill" :class="item.badgeClass">{{ item.badge }}</span>
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="trashGroup" class="collection-trash-dock">
        <button
          class="pipeline-group-toggle trash-toggle"
          type="button"
          :aria-expanded="!collapsedGroups[trashGroup.name]"
          @click="toggleGroupCollapse(trashGroup.name)"
        >
          <span
            class="pipeline-group-arrow"
            :class="{ collapsed: collapsedGroups[trashGroup.name] }"
            aria-hidden="true"
          ></span>
          <div class="pipeline-group-title">
            <strong>{{ trashLabel }}</strong>
            <span>{{ trashGroup.items.length }}</span>
          </div>
        </button>

        <div v-if="!collapsedGroups[trashGroup.name]" class="pipeline-group-items trash-items">
          <button
            v-for="item in trashGroup.items"
            :key="item.key"
            class="pipeline-template-button trash-item-button"
            :class="{ active: activeItemKey === item.key }"
            type="button"
            @click="$emit('select-item', item.raw)"
          >
            <div class="pipeline-template-row">
              <strong>{{ item.label }}</strong>
              <span v-if="item.badge" class="request-method-pill" :class="item.badgeClass">{{ item.badge }}</span>
            </div>
          </button>
        </div>
      </div>
    </section>
  </aside>

  <div v-if="showManager" class="collection-manager-backdrop" @click.self="closeManager">
    <div class="collection-manager-dialog">
      <div class="collection-manager-header">
        <div>
          <p class="eyebrow">{{ eyebrow }}</p>
          <h3>{{ managerTitle }}</h3>
        </div>
        <button class="small-button" type="button" @click="closeManager">Close</button>
      </div>

      <div class="collection-manager-toolbar">
        <input
          v-model.trim="newGroupName"
          class="collection-manager-input"
          placeholder="New group name"
          @keydown.enter.prevent="submitCreateGroup"
        />
        <button class="small-button primary-button" type="button" @click="submitCreateGroup">Create Group</button>
      </div>

      <div class="collection-manager-body">
        <div v-for="group in groups" :key="`manager-${group.name}`" class="collection-manager-group">
          <div class="collection-manager-group-header">
            <div class="collection-manager-group-title-block">
              <div class="pipeline-group-title">
                <strong v-if="editingGroup !== group.name">{{ group.isTrash ? trashLabel : group.name }}</strong>
                <input
                  v-else
                  v-model.trim="renameDrafts[group.name]"
                  class="collection-manager-input"
                  :placeholder="group.name"
                  @keydown.enter.prevent="submitRenameGroup(group)"
                />
                <span>{{ group.items.length }}</span>
              </div>
            </div>

            <div class="collection-manager-item-controls">
              <button
                v-if="group.canRename && editingGroup !== group.name"
                class="small-button"
                type="button"
                @click="startRenameGroup(group)"
              >
                Rename
              </button>
              <button
                v-if="group.canRename && editingGroup === group.name"
                class="small-button primary-button"
                type="button"
                @click="submitRenameGroup(group)"
              >
                Save
              </button>
              <button
                v-if="group.canDelete"
                class="small-button danger-button"
                type="button"
                @click="$emit('delete-group', group.name)"
              >
                Delete
              </button>
            </div>
          </div>

          <div class="collection-manager-list">
            <div v-for="item in group.items" :key="`manager-item-${item.key}`" class="collection-manager-item">
              <div class="collection-manager-item-main">
                <strong>{{ item.label }}</strong>
                <small v-if="item.subtitle">{{ item.subtitle }}</small>
              </div>
              <div class="collection-manager-item-controls">
                <select v-model="managerTargetGroups[item.key]" class="collection-manager-select">
                  <option v-for="option in movableGroupNames" :key="`${item.key}-${option}`" :value="option">
                    {{ option }}
                  </option>
                </select>
                <button class="small-button" type="button" @click="submitMoveItem(item)">Move</button>
                <button
                  class="small-button danger-button"
                  type="button"
                  @click="$emit('delete-item', { item: item.raw, permanent: Boolean(group.isTrash) })"
                >
                  delete
                </button>
              </div>
            </div>

            <div v-if="!group.items.length" class="empty-state compact-empty-state">No pipelines in this group.</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";

const props = defineProps({
  groups: { type: Array, default: () => [] },
  activeItemKey: { type: String, default: "" },
  eyebrow: { type: String, default: "Collections" },
  title: { type: String, default: "Pipelines" },
  managerTitle: { type: String, default: "Collections Editor" },
  trashGroupName: { type: String, default: "Deleted" },
  trashLabel: { type: String, default: "Deleted" },
});

const emit = defineEmits([
  "create-group",
  "rename-group",
  "delete-group",
  "move-item",
  "delete-item",
  "select-item",
  "collapse-change",
]);

const isSidebarCollapsed = ref(false);
const showManager = ref(false);
const newGroupName = ref("");
const editingGroup = ref("");
const collapsedGroups = reactive({});
const managerTargetGroups = reactive({});
const renameDrafts = reactive({});

const trashGroup = computed(() => props.groups.find((group) => group.name === props.trashGroupName) || null);
const regularGroups = computed(() => props.groups.filter((group) => group.name !== props.trashGroupName));
const movableGroupNames = computed(() => props.groups.filter((group) => !group.isTrash).map((group) => group.name));

watch(
  () =>
    props.groups
      .map((group) => `${group.name}:${group.isTrash ? "trash" : "normal"}:${(group.items || []).map((item) => item.key).join(",")}`)
      .join("|"),
  () => {
    for (const group of props.groups) {
      if (!(group.name in collapsedGroups)) {
        collapsedGroups[group.name] = true;
      }
      renameDrafts[group.name] = renameDrafts[group.name] ?? group.name;
      for (const item of group.items || []) {
        const targetGroup = group.isTrash ? movableGroupNames.value[0] || group.name : group.name;
        if (managerTargetGroups[item.key] !== targetGroup) {
          managerTargetGroups[item.key] = targetGroup;
        }
      }
    }
  },
  { immediate: true },
);

function toggleSidebar() {
  isSidebarCollapsed.value = !isSidebarCollapsed.value;
  emit("collapse-change", isSidebarCollapsed.value);
}

function toggleGroupCollapse(groupName) {
  collapsedGroups[groupName] = !collapsedGroups[groupName];
}

function closeManager() {
  showManager.value = false;
  newGroupName.value = "";
  editingGroup.value = "";
}

function submitCreateGroup() {
  const name = String(newGroupName.value || "").trim();
  if (!name) {
    return;
  }
  emit("create-group", name);
  newGroupName.value = "";
}

function startRenameGroup(group) {
  editingGroup.value = group.name;
  renameDrafts[group.name] = renameDrafts[group.name] || group.name;
}

function submitRenameGroup(group) {
  const nextName = String(renameDrafts[group.name] || "").trim();
  if (!nextName || nextName === group.name) {
    return;
  }
  editingGroup.value = "";
  emit("rename-group", { name: group.name, nextName });
}

function submitMoveItem(item) {
  const targetGroup = String(managerTargetGroups[item.key] || "").trim();
  if (!targetGroup) {
    return;
  }
  emit("move-item", { item: item.raw, targetGroup });
}
</script>
