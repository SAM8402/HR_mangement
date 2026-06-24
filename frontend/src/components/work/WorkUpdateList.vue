<template>
  <div class="work-update-list">
    <div v-if="updates.length === 0" class="empty-state">
      <p>No work updates to display.</p>
    </div>
    <div v-for="update in updates" :key="update.id" class="update-item">
      <div class="update-header">
        <h4>{{ update.title }}</h4>
        <span class="update-date">{{ formatDate(update.date) }}</span>
      </div>
      <p class="update-desc">{{ update.description }}</p>
      <div class="update-footer">
        <div class="update-tags">
          <span
            v-for="tag in (update.tags || [])"
            :key="tag"
            :class="['tag', tag]"
          >
            {{ formatTag(tag) }}
          </span>
        </div>
        <div
          v-if="canEdit && update.user_id === currentUserId"
          class="update-actions"
        >
          <button class="btn-icon" @click="$emit('edit', update)">&#9998;</button>
          <button class="btn-icon danger" @click="$emit('delete', update.id)">&#128465;</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  updates: { type: Array, default: () => [] },
  currentUserId: { type: [String, Number], default: null },
  canEdit: { type: Boolean, default: false }
})

defineEmits(['edit', 'delete'])

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric'
  })
}

function formatTag(tag) {
  const tags = {
    in_progress: 'In Progress',
    completed: 'Completed',
    blocked: 'Blocked'
  }
  return tags[tag] || tag
}
</script>

<style scoped>
.work-update-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #64748b;
  background: white;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.update-item {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 16px;
  transition: box-shadow 0.2s;
}

.update-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.update-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.update-header h4 {
  color: #1e293b;
  font-size: 0.95rem;
}

.update-date {
  font-size: 0.8rem;
  color: #94a3b8;
}

.update-desc {
  font-size: 0.9rem;
  color: #475569;
  margin-bottom: 10px;
  line-height: 1.5;
}

.update-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.update-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.tag {
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 0.72rem;
  font-weight: 500;
}

.tag.in_progress { background: #dbeafe; color: #2563eb; }
.tag.completed { background: #d1fae5; color: #059669; }
.tag.blocked { background: #fef2f2; color: #dc2626; }

.update-actions {
  display: flex;
  gap: 4px;
}

.btn-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f1f5f9;
  color: #475569;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.btn-icon:hover { background: #e2e8f0; }
.btn-icon.danger { color: #dc2626; }
.btn-icon.danger:hover { background: #fef2f2; }
</style>
