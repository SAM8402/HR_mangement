<template>
  <div class="policies-page">
    <h1>Company Policies</h1>

    <div class="tabs">
      <button
        :class="['tab-btn', { active: activeTab === 'roles' }]"
        @click="activeTab = 'roles'"
      >
        Company Roles
      </button>
      <button
        :class="['tab-btn', { active: activeTab === 'rules' }]"
        @click="activeTab = 'rules'"
      >
        Company Rules
      </button>
    </div>

    <!-- Roles Tab -->
    <div v-if="activeTab === 'roles'" class="tab-content">
      <div v-if="permissions.canManagePolicies()" class="actions-bar">
        <button class="btn-primary" @click="showRoleForm = true">+ Add Role</button>
        <label class="upload-btn">
          &#128194; Upload Role Doc (.docx/.pdf)
          <input type="file" accept=".docx,.pdf" @change="handleDocUpload" hidden />
        </label>
      </div>
 
      <div v-if="showRoleForm" class="form-card">
        <h3>{{ editingRole ? 'Edit Role' : 'Add New Role' }}</h3>
        <form @submit.prevent="handleRoleSubmit">
          <div class="form-group">
            <label>Role Name</label>
            <input v-model="roleForm.name" placeholder="e.g. Software Engineer" required />
          </div>
          <div class="form-group">
            <label>Description</label>
            <textarea v-model="roleForm.description" rows="3" placeholder="Role description..."></textarea>
          </div>
          <div class="form-group">
            <label>Permissions (comma separated)</label>
            <input v-model="roleForm.permissions" placeholder="e.g. leave.apply, leave.approve" />
          </div>
          <div class="form-actions">
            <button type="submit" class="btn-primary">Save</button>
            <button type="button" class="btn-secondary" @click="cancelRoleEdit">Cancel</button>
          </div>
        </form>
      </div>

      <div class="policy-list">
        <div v-if="roles.length === 0" class="empty-state">No roles defined yet.</div>
        <div v-for="role in roles" :key="role.id" class="policy-item">
          <div class="policy-info">
            <h4>{{ role.name }}</h4>
            <p>{{ role.description }}</p>
            <div v-if="role.permissions" class="tags">
              <span v-for="p in role.permissions" :key="p" class="tag">{{ p }}</span>
            </div>
          </div>
          <div v-if="permissions.canManagePolicies()" class="policy-actions">
            <button class="btn-icon" @click="editRole(role)">&#9998;</button>
            <button class="btn-icon danger" @click="handleDeleteRole(role.id)">&#128465;</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Rules Tab -->
    <div v-if="activeTab === 'rules'" class="tab-content">
      <div v-if="permissions.canManagePolicies()" class="actions-bar">
        <button class="btn-primary" @click="showRuleForm = true">+ Add Rule</button>
        <label class="upload-btn">
          &#128194; Upload Rule PDF/Doc
          <input type="file" accept=".docx,.pdf" @change="handleRuleDocUpload" hidden />
        </label>
      </div>

      <div v-if="showRuleForm" class="form-card">
        <h3>{{ editingRule ? 'Edit Rule' : 'Add New Rule' }}</h3>
        <form @submit.prevent="handleRuleSubmit">
          <div class="form-group">
            <label>Category</label>
            <input v-model="ruleForm.category" placeholder="e.g. Attendance, Conduct" required />
          </div>
          <div class="form-group">
            <label>Title</label>
            <input v-model="ruleForm.title" placeholder="Rule title" required />
          </div>
          <div class="form-group">
            <label>Description</label>
            <textarea v-model="ruleForm.description" rows="3" placeholder="Rule details..."></textarea>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn-primary">Save</button>
            <button type="button" class="btn-secondary" @click="cancelRuleEdit">Cancel</button>
          </div>
        </form>
      </div>

      <div class="policy-list">
        <div v-if="rules.length === 0" class="empty-state">No rules defined yet.</div>
        <div v-for="rule in rules" :key="rule.id" class="policy-item">
          <div class="policy-info">
            <span class="category-badge">{{ rule.category }}</span>
            <h4>{{ rule.title }}</h4>
            <p>{{ rule.description }}</p>
          </div>
          <div v-if="permissions.canManagePolicies()" class="policy-actions">
            <button class="btn-icon" @click="editRule(rule)">&#9998;</button>
            <button class="btn-icon danger" @click="handleDeleteRule(rule.id)">&#128465;</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getRoles, createRole, updateRole, deleteRole, uploadDoc } from '../api/roles.js'
import { getRules, createRule, updateRule, deleteRule, uploadRuleDoc } from '../api/rules.js'
import { usePermissions } from '../composables/usePermissions.js'

const permissions = usePermissions()

const activeTab = ref('roles')
const roles = ref([])
const rules = ref([])

const showRoleForm = ref(false)
const editingRole = ref(null)
const roleForm = ref({ name: '', description: '', permissions: '' })

const showRuleForm = ref(false)
const editingRule = ref(null)
const ruleForm = ref({ category: '', title: '', description: '' })

async function fetchRoles() {
  try {
    const res = await getRoles()
    roles.value = res.data || []
  } catch {
    roles.value = []
  }
}

async function fetchRules() {
  try {
    const res = await getRules()
    rules.value = res.data || []
  } catch {
    rules.value = []
  }
}

function editRole(role) {
  editingRole.value = role.id
  roleForm.value = {
    name: role.name,
    description: role.description || '',
    permissions: Array.isArray(role.permissions) ? role.permissions.join(', ') : (role.permissions || '')
  }
  showRoleForm.value = true
}

function cancelRoleEdit() {
  showRoleForm.value = false
  editingRole.value = null
  roleForm.value = { name: '', description: '', permissions: '' }
}

async function handleRoleSubmit() {
  const data = {
    ...roleForm.value,
    permissions: roleForm.value.permissions.split(',').map(p => p.trim()).filter(Boolean)
  }

  if (editingRole.value) {
    await updateRole(editingRole.value, data)
  } else {
    await createRole(data)
  }
  cancelRoleEdit()
  await fetchRoles()
}

async function handleDeleteRole(id) {
  if (confirm('Delete this role?')) {
    await deleteRole(id)
    await fetchRoles()
  }
}

async function handleDocUpload(event) {
  const file = event.target.files[0]
  if (file) {
    await uploadDoc(file)
    await fetchRoles()
  }
}

async function handleRuleDocUpload(event) {
  const file = event.target.files[0]
  if (file) {
    await uploadRuleDoc(file)
    await fetchRules()
  }
}


function editRule(rule) {
  editingRule.value = rule.id
  ruleForm.value = {
    category: rule.category,
    title: rule.title,
    description: rule.description || ''
  }
  showRuleForm.value = true
}

function cancelRuleEdit() {
  showRuleForm.value = false
  editingRule.value = null
  ruleForm.value = { category: '', title: '', description: '' }
}

async function handleRuleSubmit() {
  if (editingRule.value) {
    await updateRule(editingRule.value, ruleForm.value)
  } else {
    await createRule(ruleForm.value)
  }
  cancelRuleEdit()
  await fetchRules()
}

async function handleDeleteRule(id) {
  if (confirm('Delete this rule?')) {
    await deleteRule(id)
    await fetchRules()
  }
}

onMounted(() => {
  fetchRoles()
  fetchRules()
})
</script>

<style scoped>
.policies-page {
  max-width: 900px;
  margin: 0 auto;
}

.policies-page h1 {
  font-size: 1.5rem;
  color: #1e293b;
  margin-bottom: 20px;
}

.tabs {
  display: flex;
  gap: 4px;
  border-bottom: 2px solid #e2e8f0;
  margin-bottom: 24px;
}

.tab-btn {
  padding: 10px 20px;
  background: none;
  color: #64748b;
  font-weight: 500;
  font-size: 0.9rem;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.2s;
}

.tab-btn:hover { color: #2563eb; }
.tab-btn.active { color: #2563eb; border-bottom-color: #2563eb; }

.actions-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
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

.upload-btn {
  padding: 8px 16px;
  background: white;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 0.85rem;
  cursor: pointer;
  transition: border-color 0.2s;
}

.upload-btn:hover { border-color: #2563eb; }

.form-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
  margin-bottom: 20px;
}

.form-card h3 {
  font-size: 1rem;
  color: #334155;
  margin-bottom: 16px;
}

.form-group {
  margin-bottom: 14px;
}

.form-group label {
  display: block;
  font-weight: 500;
  color: #334155;
  font-size: 0.85rem;
  margin-bottom: 4px;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.9rem;
  outline: none;
}

.form-group input:focus,
.form-group textarea:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.form-actions {
  display: flex;
  gap: 8px;
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

.policy-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.policy-item {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.policy-info h4 {
  color: #1e293b;
  margin-bottom: 4px;
}

.policy-info p {
  color: #64748b;
  font-size: 0.85rem;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 8px;
}

.tag {
  background: #dbeafe;
  color: #2563eb;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
}

.category-badge {
  display: inline-block;
  background: #fef3c7;
  color: #92400e;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  margin-bottom: 6px;
}

.policy-actions {
  display: flex;
  gap: 4px;
}

.btn-icon {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f1f5f9;
  color: #475569;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.btn-icon:hover { background: #e2e8f0; }
.btn-icon.danger { color: #dc2626; }
.btn-icon.danger:hover { background: #fef2f2; }

.empty-state {
  text-align: center;
  padding: 40px;
  color: #64748b;
  background: white;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}
</style>
