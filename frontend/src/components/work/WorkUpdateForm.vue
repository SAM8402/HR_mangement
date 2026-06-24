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
        <label>Department</label>
        <select v-model="form.department" class="form-select">
          <option value="">— Select Department —</option>
          <option v-for="dept in departments" :key="dept" :value="dept">
            {{ dept }}
          </option>
        </select>
      </div>
    </div>
    <div class="form-row">
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
      <div v-if="isPrivilegedUser" class="form-group">
        <label>Assign to User</label>
        <select v-model="form.assigned_user_id" class="form-select">
          <option value="">— Self (default) —</option>
          <option v-for="u in usersList" :key="u.id" :value="u.id">
            {{ u.name }} ({{ u.email }})
          </option>
        </select>
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
import { ref, watch, computed, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth.js'
import { getDepartments } from '../../api/departments.js'
import { getUsers } from '../../api/users.js'

const props = defineProps({
  initialData: { type: Object, default: null },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['submit', 'cancel'])

const authStore = useAuthStore()
const departments = ref([])
const usersList = ref([])

const isPrivilegedUser = computed(() =>
  ['admin', 'manager', 'hr'].includes(authStore.userRole)
)

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
  department: '',
  assigned_user_id: '',
  tags: []
})

const isEditing = computed(() => !!props.initialData)

watch(() => props.initialData, (data) => {
  if (data) {
    form.value = {
      title: data.title || '',
      description: data.description || '',
      date: data.date || today,
      department: data.department || '',
      assigned_user_id: '',
      tags: Array.isArray(data.tags) ? [...data.tags] : []
    }
  } else {
    form.value = { title: '', description: '', date: today, department: '', assigned_user_id: '', tags: [] }
  }
}, { immediate: true })

function handleSubmit() {
  const payload = { ...form.value }
  // Clean up empty optional fields
  if (!payload.department) delete payload.department
  if (!payload.assigned_user_id) delete payload.assigned_user_id
  emit('submit', payload)
  if (!isEditing.value) {
    form.value = { title: '', description: '', date: today, department: '', assigned_user_id: '', tags: [] }
  }
}

onMounted(async () => {
  try {
    const res = await getDepartments()
    departments.value = res.data
  } catch {
    departments.value = []
  }

  if (isPrivilegedUser.value) {
    try {
      const res = await getUsers()
      usersList.value = res.data.users
    } catch {
      usersList.value = []
    }
  }
})
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
.form-group textarea,
.form-select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.9rem;
  outline: none;
  transition: border-color 0.2s;
  background: white;
}

.form-group input:focus,
.form-group textarea:focus,
.form-select:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.form-group textarea {
  resize: vertical;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
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
