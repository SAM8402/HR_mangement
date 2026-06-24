<template>
  <form @submit.prevent="handleSubmit" class="update-form">
    <div class="form-group">
      <label>Title</label>
      <input
        v-model="form.title"
        type="text"
        placeholder="Brief title for your update"
        required
      />
    </div>
    <div class="form-group">
      <label>Description</label>
      <textarea
        v-model="form.description"
        rows="3"
        placeholder="What did you work on?"
        required
      ></textarea>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Date</label>
        <input v-model="form.date" type="date" required />
      </div>
      <div class="form-group">
        <label>Tags</label>
        <div class="tags-group">
          <label
            v-for="tag in tagOptions"
            :key="tag.value"
            :class="['tag-checkbox', { checked: form.tags.includes(tag.value) }]"
          >
            <input
              type="checkbox"
              :value="tag.value"
              v-model="form.tags"
              class="hidden-check"
            />
            {{ tag.label }}
          </label>
        </div>
      </div>
    </div>
    <div class="form-actions">
      <button type="submit" class="btn-primary" :disabled="loading">
        {{ loading ? 'Saving...' : (isEditing ? 'Update' : 'Add Update') }}
      </button>
      <button v-if="isEditing" type="button" class="btn-secondary" @click="$emit('cancel')">
        Cancel
      </button>
    </div>
  </form>
</template>

<script setup>
import { ref, watch, computed } from 'vue'

const props = defineProps({
  initialData: { type: Object, default: null },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['submit', 'cancel'])

const tagOptions = [
  { label: 'In Progress', value: 'in_progress' },
  { label: 'Completed', value: 'completed' },
  { label: 'Blocked', value: 'blocked' }
]

const today = new Date().toISOString().split('T')[0]

const form = ref({
  title: '',
  description: '',
  date: today,
  tags: []
})

const isEditing = computed(() => !!props.initialData)

watch(() => props.initialData, (data) => {
  if (data) {
    form.value = {
      title: data.title || '',
      description: data.description || '',
      date: data.date || today,
      tags: Array.isArray(data.tags) ? [...data.tags] : []
    }
  } else {
    form.value = { title: '', description: '', date: today, tags: [] }
  }
}, { immediate: true })

function handleSubmit() {
  emit('submit', { ...form.value })
  if (!isEditing.value) {
    form.value = { title: '', description: '', date: today, tags: [] }
  }
}
</script>

<style scoped>
.form-group {
  margin-bottom: 14px;
}

.form-group label {
  display: block;
  font-weight: 500;
  color: #334155;
  font-size: 0.85rem;
  margin-bottom: 6px;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.9rem;
  outline: none;
  transition: border-color 0.2s;
}

.form-group input:focus,
.form-group textarea:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.form-group textarea {
  resize: vertical;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: 16px;
}

.tags-group {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.tag-checkbox {
  padding: 4px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 16px;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}

.tag-checkbox.checked {
  background: #dbeafe;
  border-color: #2563eb;
  color: #2563eb;
}

.hidden-check {
  display: none;
}

.form-actions {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.btn-primary {
  padding: 8px 20px;
  background: #2563eb;
  color: white;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.9rem;
  transition: background 0.2s;
}

.btn-primary:hover:not(:disabled) { background: #1d4ed8; }
.btn-primary:disabled { opacity: 0.7; cursor: not-allowed; }

.btn-secondary {
  padding: 8px 20px;
  background: #f1f5f9;
  color: #475569;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.9rem;
}

.btn-secondary:hover { background: #e2e8f0; }
</style>
