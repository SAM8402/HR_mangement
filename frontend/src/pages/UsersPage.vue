<template>
  <div class="users-page">
    <div class="page-header">
      <h1>User Management</h1>
      <button class="btn-primary" @click="openAddModal">+ Add User</button>
    </div>

    <div class="search-bar">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search by name or email..."
        class="search-input"
      />
      <select v-model="filterRole" class="filter-select">
        <option value="">All Roles</option>
        <option value="admin">Admin</option>
        <option value="manager">Manager</option>
        <option value="hr">HR</option>
        <option value="employee">Employee</option>
      </select>
    </div>

    <div class="table-card">
      <table class="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Role</th>
            <th>Department</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="6" class="loading-cell">Loading users...</td>
          </tr>
          <tr v-else-if="filteredUsers.length === 0">
            <td colspan="6" class="empty-cell">No users found.</td>
          </tr>
          <tr v-for="user in filteredUsers" :key="user.id">
            <td>{{ user.name }}</td>
            <td>{{ user.email }}</td>
            <td>
              <span :class="['role-badge', user.role]">{{ user.role }}</span>
            </td>
            <td>{{ user.department || '-' }}</td>
            <td>
              <span :class="['status-badge', user.is_active !== false ? 'active' : 'inactive']">
                {{ user.is_active !== false ? 'Active' : 'Inactive' }}
              </span>
            </td>
            <td>
              <div class="action-buttons">
                <button class="btn-sm" @click="openEditModal(user)">Edit</button>
                <button class="btn-sm danger" @click="handleDelete(user.id)">Deactivate</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Add/Edit Modal -->
    <Modal :show="showModal" @close="showModal = false">
      <template #title>{{ editingUserId ? 'Edit User' : 'Add New User' }}</template>
      <form @submit.prevent="handleSaveUser" class="user-form">
        <div class="form-group">
          <label>Full Name</label>
          <input v-model="userForm.name" type="text" placeholder="John Doe" required />
        </div>
        <div class="form-group">
          <label>Email</label>
          <input v-model="userForm.email" type="email" placeholder="john@company.com" required />
        </div>
        <div v-if="!editingUserId" class="form-group">
          <label>Password</label>
          <input v-model="userForm.password" type="password" placeholder="Min 6 characters" required />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Role</label>
            <select v-model="userForm.role" required>
              <option value="employee">Employee</option>
              <option value="manager">Manager</option>
              <option value="hr">HR</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <div class="form-group">
            <label>Department</label>
            <input v-model="userForm.department" type="text" placeholder="Engineering" />
          </div>
        </div>
        <div class="form-group">
          <label>Phone</label>
          <input v-model="userForm.phone" type="text" placeholder="+1 234 567 890" />
        </div>
        <div class="modal-actions">
          <button type="button" class="btn-secondary" @click="showModal = false">Cancel</button>
          <button type="submit" class="btn-primary" :disabled="saving">
            {{ saving ? 'Saving...' : 'Save User' }}
          </button>
        </div>
      </form>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getUsers, createUser, updateUser, deleteUser } from '../api/users.js'
import Modal from '../components/common/Modal.vue'

const users = ref([])
const loading = ref(false)
const saving = ref(false)
const showModal = ref(false)
const editingUserId = ref(null)
const searchQuery = ref('')
const filterRole = ref('')

const userForm = ref({
  name: '',
  email: '',
  password: '',
  role: 'employee',
  department: '',
  phone: ''
})

const filteredUsers = computed(() => {
  return users.value.filter(u => {
    const matchesSearch = !searchQuery.value ||
      u.name?.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      u.email?.toLowerCase().includes(searchQuery.value.toLowerCase())
    const matchesRole = !filterRole.value || u.role === filterRole.value
    return matchesSearch && matchesRole
  })
})

async function fetchUsers() {
  loading.value = true
  try {
    const res = await getUsers()
    users.value = res.data?.users || []
  } catch {
    users.value = []
  } finally {
    loading.value = false
  }
}

function openAddModal() {
  editingUserId.value = null
  userForm.value = { name: '', email: '', password: '', role: 'employee', department: '', phone: '' }
  showModal.value = true
}

function openEditModal(user) {
  editingUserId.value = user.id
  userForm.value = {
    name: user.name,
    email: user.email,
    password: '',
    role: user.role,
    department: user.department || '',
    phone: user.phone || ''
  }
  showModal.value = true
}

async function handleSaveUser() {
  saving.value = true
  try {
    const data = { ...userForm.value }
    if (editingUserId.value) {
      if (!data.password) delete data.password
      await updateUser(editingUserId.value, data)
    } else {
      await createUser(data)
    }
    showModal.value = false
    await fetchUsers()
  } catch {
    // error handled by interceptor
  } finally {
    saving.value = false
  }
}

async function handleDelete(id) {
  if (confirm('Are you sure you want to deactivate this user?')) {
    await deleteUser(id)
    await fetchUsers()
  }
}

onMounted(fetchUsers)
</script>

<style scoped>
.users-page {
  max-width: 1100px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  font-size: 1.5rem;
  color: #1e293b;
}

.btn-primary {
  padding: 8px 16px;
  background: #2563eb;
  color: white;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.85rem;
  transition: background 0.2s;
}

.btn-primary:hover { background: #1d4ed8; }
.btn-primary:disabled { opacity: 0.7; cursor: not-allowed; }

.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.search-input {
  flex: 1;
  padding: 8px 14px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 0.9rem;
  outline: none;
}

.search-input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 0.9rem;
  outline: none;
}

.table-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  text-align: left;
  padding: 12px 16px;
  font-size: 0.8rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid #e2e8f0;
}

.data-table td {
  padding: 12px 16px;
  font-size: 0.9rem;
  color: #334155;
  border-bottom: 1px solid #f1f5f9;
}

.data-table tr:last-child td {
  border-bottom: none;
}

.data-table tr:hover td {
  background: #f8fafc;
}

.loading-cell,
.empty-cell {
  text-align: center;
  color: #64748b;
  padding: 40px 16px !important;
}

.role-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: capitalize;
}

.role-badge.admin { background: #ede9fe; color: #7c3aed; }
.role-badge.manager { background: #dbeafe; color: #2563eb; }
.role-badge.hr { background: #d1fae5; color: #059669; }
.role-badge.employee { background: #f1f5f9; color: #475569; }

.status-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
}

.status-badge.active { background: #d1fae5; color: #059669; }
.status-badge.inactive { background: #fef2f2; color: #dc2626; }

.action-buttons {
  display: flex;
  gap: 6px;
}

.btn-sm {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  background: #f1f5f9;
  color: #475569;
  transition: all 0.2s;
}

.btn-sm:hover { background: #e2e8f0; }
.btn-sm.danger { color: #dc2626; }
.btn-sm.danger:hover { background: #fef2f2; }

.user-form .form-group {
  margin-bottom: 14px;
}

.user-form label {
  display: block;
  font-weight: 500;
  color: #334155;
  font-size: 0.85rem;
  margin-bottom: 4px;
}

.user-form input,
.user-form select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.9rem;
  outline: none;
}

.user-form input:focus,
.user-form select:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}

.btn-secondary {
  padding: 8px 16px;
  background: #f1f5f9;
  color: #475569;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.85rem;
}

.btn-secondary:hover { background: #e2e8f0; }
</style>
