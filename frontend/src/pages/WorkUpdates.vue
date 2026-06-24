<template>
  <div class="work-updates-page">
    <h1>Work Updates</h1>

    <div class="form-card">
      <h2>{{ editingId ? 'Edit Update' : 'Add Work Update' }}</h2>
      <WorkUpdateForm
        :initial-data="editingUpdate"
        @submit="handleSubmit"
        @cancel="cancelEdit"
      />
    </div>

    <div class="updates-section">
      <div class="section-header" v-if="permissions.canViewAllLeaves()">
        <div class="filter-bar">
          <label>View:</label>
          <select v-model="viewMode" class="filter-select">
            <option value="my">My Updates</option>
            <option value="all">All Updates</option>
          </select>
        </div>
      </div>

      <WorkUpdateList
        :updates="displayedUpdates"
        :current-user-id="authStore.user?.id"
        :can-edit="true"
        @edit="handleEdit"
        @delete="handleDelete"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useWorkUpdateStore } from '../stores/workUpdates.js'
import { useAuthStore } from '../stores/auth.js'
import { usePermissions } from '../composables/usePermissions.js'
import WorkUpdateForm from '../components/work/WorkUpdateForm.vue'
import WorkUpdateList from '../components/work/WorkUpdateList.vue'

const workUpdateStore = useWorkUpdateStore()
const authStore = useAuthStore()
const permissions = usePermissions()

const viewMode = ref('my')
const editingId = ref(null)
const editingUpdate = ref(null)

const displayedUpdates = computed(() => {
  if (viewMode.value === 'all') {
    return workUpdateStore.allUpdates
  }
  return workUpdateStore.myUpdates
})

function handleEdit(update) {
  editingId.value = update.id
  editingUpdate.value = { ...update }
}

function cancelEdit() {
  editingId.value = null
  editingUpdate.value = null
}

async function handleSubmit(data) {
  if (editingId.value) {
    await workUpdateStore.updateUpdate(editingId.value, data)
    cancelEdit()
  } else {
    await workUpdateStore.createUpdate(data)
  }
}

async function handleDelete(id) {
  if (confirm('Are you sure you want to delete this update?')) {
    await workUpdateStore.deleteUpdate(id)
  }
}

watch(viewMode, (mode) => {
  if (mode === 'all' && permissions.canViewAllLeaves()) {
    workUpdateStore.fetchAllUpdates()
  } else {
    workUpdateStore.fetchMyUpdates()
  }
})

onMounted(() => {
  workUpdateStore.fetchMyUpdates()
  if (permissions.canViewAllLeaves()) {
    workUpdateStore.fetchAllUpdates()
  }
})
</script>

<style scoped>
.work-updates-page {
  max-width: 900px;
  margin: 0 auto;
}

.work-updates-page h1 {
  font-size: 1.5rem;
  color: #1e293b;
  margin-bottom: 20px;
}

.form-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
  margin-bottom: 24px;
}

.form-card h2 {
  font-size: 1.1rem;
  color: #334155;
  margin-bottom: 16px;
}

.updates-section {
  margin-top: 8px;
}

.section-header {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  color: #475569;
}

.filter-select {
  padding: 6px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.9rem;
  outline: none;
}

.filter-select:focus {
  border-color: #2563eb;
}
</style>
