<template>
  <aside class="sidebar-shell sidebar-shell-compact" :class="{ collapsed: isSidebarCollapsed }">
    <header class="sidebar-header">
      <div v-if="!isSidebarCollapsed">
        <p class="eyebrow">{{ eyebrow }}</p>
        <h2>{{ title }}</h2>
      </div>
      <div class="sidebar-header-actions">
        <button v-if="!isSidebarCollapsed" class="ui-btn" type="button" @click="showManager = true">Edit</button>
        <button
          class="sidebar-collapse-button ui-icon-collapse ui-icon-btn"
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
      <div class="collection-sidebar-scroll" @contextmenu.prevent="openBlankContextMenu($event)">
        <div class="pipeline-template-list ui-tree">
          <div v-for="group in regularGroups" :key="group.name" class="pipeline-group-section ui-tree-branch">
            <button
              class="pipeline-group-toggle ui-list-item ui-tree-node"
              type="button"
              :aria-expanded="!collapsedGroups[group.name]"
              @click="toggleGroupCollapse(group.name)"
              @contextmenu.prevent.stop="openGroupContextMenu($event, group)"
            >
              <span
                class="pipeline-group-arrow ui-tree-caret"
                :class="{ collapsed: collapsedGroups[group.name] }"
                aria-hidden="true"
              ></span>
              <div class="pipeline-group-title ui-tree-content">
                <strong>{{ group.name }}</strong>
                <span>{{ group.items.length }}</span>
              </div>
            </button>

            <div v-if="!collapsedGroups[group.name]" class="pipeline-group-items ui-tree-children">
              <button
                v-for="item in group.items"
                :key="item.key"
                class="pipeline-template-button ui-list-item ui-tree-node"
                :class="{ active: activeItemKey === item.key }"
                type="button"
                @click="$emit('select-item', item.raw)"
                @contextmenu.prevent.stop="openItemContextMenu($event, item, group)"
              >
                <div class="pipeline-template-row ui-tree-content">
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
          class="pipeline-group-toggle trash-toggle ui-list-item ui-tree-node"
          type="button"
          :aria-expanded="!collapsedGroups[trashGroup.name]"
          @click="toggleGroupCollapse(trashGroup.name)"
        >
          <span
            class="pipeline-group-arrow ui-tree-caret"
            :class="{ collapsed: collapsedGroups[trashGroup.name] }"
            aria-hidden="true"
          ></span>
          <div class="pipeline-group-title ui-tree-content">
            <strong>{{ trashLabel }}</strong>
            <span>{{ trashGroup.items.length }}</span>
          </div>
        </button>

        <div v-if="!collapsedGroups[trashGroup.name]" class="pipeline-group-items trash-items ui-tree-children">
          <button
            v-for="item in trashGroup.items"
            :key="item.key"
            class="pipeline-template-button trash-item-button ui-list-item ui-tree-node"
            :class="{ active: activeItemKey === item.key }"
            type="button"
            @click="$emit('select-item', item.raw)"
            @contextmenu.prevent.stop="openItemContextMenu($event, item, trashGroup)"
          >
            <div class="pipeline-template-row ui-tree-content">
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
        <button class="ui-action-close ui-icon-close ui-btn ui-icon-btn" type="button" title="Close" aria-label="Close collections editor" @click="closeManager"><svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg></button>
      </div>

      <div class="collection-manager-toolbar">
        <input
          v-model.trim="newGroupName"
          class="collection-manager-input"
          placeholder="New group name"
          @keydown.enter.prevent="submitCreateGroup"
        />
        <button class="ui-btn ui-btn-primary" type="button" @click="submitCreateGroup">Create Group</button>
      </div>

      <div class="collection-manager-body">
        <div v-for="group in groups" :key="`manager-${group.name}`" class="collection-manager-group">
          <div class="collection-manager-group-header">
            <div class="collection-manager-group-title-block">
              <div class="pipeline-group-title ui-tree-content">
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
                class="ui-btn"
                type="button"
                @click="startRenameGroup(group)"
              >
                Rename
              </button>
              <button
                v-if="group.canRename && editingGroup === group.name"
                class="ui-btn ui-btn-primary"
                type="button"
                @click="submitRenameGroup(group)"
              >
                Save
              </button>
              <button
                v-if="group.canDelete"
                class="ui-action-delete ui-icon-delete ui-btn ui-btn-danger"
                type="button"
                @click="$emit('delete-group', group.name)"
              >
                <span class="ui-action-label">Delete</span>
              </button>
            </div>
          </div>

          <div class="collection-manager-list">
            <div v-for="item in group.items" :key="`manager-item-${item.key}`" class="collection-manager-item ui-list-item">
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
                <button class="ui-btn" type="button" @click="submitMoveItem(item)">Move</button>
                <button
                  class="ui-action-delete ui-icon-delete ui-btn ui-btn-danger"
                  type="button"
                  @click="$emit('delete-item', { item: item.raw, permanent: Boolean(group.isTrash) })"
                >
                  <span class="ui-action-label">Delete</span>
                </button>
              </div>
            </div>

            <div v-if="!group.items.length" class="empty-state compact-empty-state">No pipelines in this group.</div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div
    v-if="contextMenu.visible"
    class="collection-context-menu"
    :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
    @click.stop
    @contextmenu.prevent
  >
    <template v-if="contextMenu.type === 'item' && contextMenu.item">
      <button type="button" @click="createPipelineInGroup(contextMenu.group?.name || '')">New pipeline in this group</button>
      <button type="button" @click="cloneItem(contextMenu.item)">Clone</button>
      <button class="ui-action-delete ui-icon-delete" type="button" @click="deleteItem(contextMenu.item, Boolean(contextMenu.group?.isTrash))"><span class="ui-action-label">Delete</span></button>
      <div class="collection-context-separator"></div>
      <p class="collection-context-label">Move to...</p>
      <button
        v-for="target in moveTargetsForContextItem"
        :key="'context-move-' + target"
        type="button"
        @click="moveItem(contextMenu.item, target)"
      >
        {{ target }}
      </button>
      <button v-if="!moveTargetsForContextItem.length" type="button" disabled>No available group</button>
    </template>

    <template v-else-if="contextMenu.type === 'group' && contextMenu.group">
      <button type="button" @click="createPipelineInGroup(contextMenu.group.name)">New pipeline</button>
      <button v-if="contextMenu.group.canRename" type="button" @click="renameGroupFromContext(contextMenu.group)">Rename group</button>
      <button v-if="contextMenu.group.canDelete" class="ui-action-delete ui-icon-delete" type="button" @click="deleteGroupFromContext(contextMenu.group)"><span class="ui-action-label">Delete</span></button>
      <button type="button" disabled>Paste / Move here</button>
    </template>

    <template v-else>
      <button type="button" @click="createPipelineInGroup('')">New pipeline</button>
    </template>
  </div>

</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";

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
  "new-item",
  "clone-item",
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
const contextMenu = reactive({
  visible: false,
  type: "blank",
  x: 0,
  y: 0,
  group: null,
  item: null,
});

const trashGroup = computed(() => props.groups.find((group) => group.name === props.trashGroupName) || null);
const regularGroups = computed(() => props.groups.filter((group) => group.name !== props.trashGroupName));
const movableGroupNames = computed(() => props.groups.filter((group) => !group.isTrash).map((group) => group.name));
const moveTargetsForContextItem = computed(() => {
  if (!contextMenu.item) {
    return [];
  }
  const currentGroupName = contextMenu.group?.name || "";
  return movableGroupNames.value.filter((name) => name && name !== currentGroupName);
});

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

onMounted(() => {
  window.addEventListener("click", closeContextMenu);
  window.addEventListener("blur", closeContextMenu);
  window.addEventListener("keydown", handleContextMenuKeydown);
});

onBeforeUnmount(() => {
  window.removeEventListener("click", closeContextMenu);
  window.removeEventListener("blur", closeContextMenu);
  window.removeEventListener("keydown", handleContextMenuKeydown);
});

function handleContextMenuKeydown(event) {
  if (event.key === "Escape") {
    closeContextMenu();
  }
}

function openContextMenu(event, payload) {
  const menuWidth = 240;
  const menuHeight = 320;
  contextMenu.visible = true;
  contextMenu.type = payload.type;
  contextMenu.group = payload.group || null;
  contextMenu.item = payload.item || null;
  contextMenu.x = Math.min(event.clientX, Math.max(8, window.innerWidth - menuWidth - 8));
  contextMenu.y = Math.min(event.clientY, Math.max(8, window.innerHeight - menuHeight - 8));
}

function openBlankContextMenu(event) {
  openContextMenu(event, { type: "blank" });
}

function openGroupContextMenu(event, group) {
  openContextMenu(event, { type: "group", group });
}

function openItemContextMenu(event, item, group) {
  openContextMenu(event, { type: "item", item, group });
}

function closeContextMenu() {
  contextMenu.visible = false;
}

function createPipelineInGroup(groupName) {
  emit("new-item", { groupName: groupName || "Ungrouped" });
  closeContextMenu();
}

function cloneItem(item) {
  emit("clone-item", { item: item.raw });
  closeContextMenu();
}

function deleteItem(item, permanent) {
  emit("delete-item", { item: item.raw, permanent });
  closeContextMenu();
}

function moveItem(item, targetGroup) {
  emit("move-item", { item: item.raw, targetGroup });
  closeContextMenu();
}

function renameGroupFromContext(group) {
  closeContextMenu();
  showManager.value = true;
  startRenameGroup(group);
}

function deleteGroupFromContext(group) {
  emit("delete-group", group.name);
  closeContextMenu();
}

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
