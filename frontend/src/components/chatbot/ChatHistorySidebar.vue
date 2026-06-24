<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <h3>Sessions</h3>
      <button class="btn-new" @click="handleNew" title="New chat">+</button>
    </div>

    <div class="session-list" v-if="sessions.length">
      <div
        v-for="s in sortedSessions"
        :key="s.session_id"
        class="session-item"
        :class="{ active: s.session_id === currentId }"
        @click="handleSelect(s.session_id)"
      >
        <template v-if="editingId === s.session_id">
          <input
            class="edit-input"
            v-model="editTitle"
            @blur="handleRename(s.session_id)"
            @keyup.enter="handleRename(s.session_id)"
            @keyup.escape="editingId = null"
            ref="editRef"
            autofocus
          />
        </template>
        <template v-else>
          <span class="session-title">{{ s.title || 'New Chat' }}</span>
          <span class="session-meta">{{ s.message_count || 0 }} msgs</span>
        </template>

        <div class="session-actions" v-if="editingId !== s.session_id">
          <button class="btn-icon" title="Rename" @click.stop="startRename(s)">&#9998;</button>
          <button class="btn-icon" title="Delete" @click.stop="handleDelete(s.session_id)">&#10005;</button>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">No sessions yet</div>
  </aside>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'

const props = defineProps({
  sessions: { type: Array, default: () => [] },
  currentId: { type: String, default: null },
})

const emit = defineEmits(['select-session', 'new-session', 'delete-session', 'rename-session'])

const editingId = ref(null)
const editTitle = ref('')
const editRef = ref(null)

const sortedSessions = computed(() => {
  return [...props.sessions].sort((a, b) => {
    const da = a.updated_at || a.created_at || ''
    const db = b.updated_at || b.created_at || ''
    return db.localeCompare(da)
  })
})

function handleSelect(id) {
  if (id !== props.currentId) {
    emit('select-session', id)
  }
}

function handleNew() {
  emit('new-session')
}

function handleDelete(id) {
  emit('delete-session', id)
}

function startRename(session) {
  editingId.value = session.session_id
  editTitle.value = session.title || 'New Chat'
  nextTick(() => {
    editRef.value?.focus()
    editRef.value?.select()
  })
}

function handleRename(id) {
  const title = editTitle.value.trim()
  if (title) {
    emit('rename-session', id, title)
  }
  editingId.value = null
}
</script>

<style scoped>
.sidebar {
  width: 260px;
  background: #f8fafc;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  height: 100%;
  flex-shrink: 0;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #e2e8f0;
}

.sidebar-header h3 {
  font-size: 0.95rem;
  color: #1e293b;
  margin: 0;
}

.btn-new {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: #2563eb;
  color: white;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  cursor: pointer;
}

.btn-new:hover {
  background: #1d4ed8;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  margin-bottom: 2px;
}

.session-item:hover {
  background: #e2e8f0;
}

.session-item.active {
  background: #dbeafe;
  color: #1e40af;
}

.session-title {
  flex: 1;
  font-size: 0.85rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-meta {
  font-size: 0.7rem;
  color: #94a3b8;
  flex-shrink: 0;
}

.edit-input {
  flex: 1;
  font-size: 0.85rem;
  padding: 4px 6px;
  border: 1px solid #2563eb;
  border-radius: 4px;
  outline: none;
  background: white;
}

.session-actions {
  display: flex;
  gap: 2px;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.15s;
}

.session-item:hover .session-actions {
  opacity: 1;
}

.btn-icon {
  width: 22px;
  height: 22px;
  border-radius: 4px;
  border: none;
  background: transparent;
  color: #64748b;
  font-size: 0.7rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.btn-icon:hover {
  background: #cbd5e1;
  color: #1e293b;
}

.empty-state {
  padding: 24px 16px;
  text-align: center;
  color: #94a3b8;
  font-size: 0.85rem;
}
</style>
