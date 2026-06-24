<template>
  <div class="leave-page">
    <h1>Leave Management</h1>

    <LeaveBalanceWidget />

    <div class="tabs">
      <button
        v-for="tab in availableTabs"
        :key="tab.key"
        :class="['tab-btn', { active: activeTab === tab.key }]"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Apply Leave Tab -->
    <div v-if="activeTab === 'apply'" class="tab-content">
      <div class="form-card">
        <h2>Apply for Leave</h2>
        <form @submit.prevent="handleApplyLeave">
          <div class="form-row">
            <div class="form-group">
              <label>Leave Type</label>
              <select v-model="leaveForm.leave_type" required>
                <option value="">Select type</option>
                <option value="casual">Casual Leave</option>
                <option value="sick">Sick Leave</option>
                <option value="earned">Earned Leave</option>
                <option value="paid">Paid Leave</option>
                <option value="unpaid">Unpaid Leave</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>From Date</label>
              <input type="date" v-model="leaveForm.from_date" required />
            </div>
            <div class="form-group">
              <label>To Date</label>
              <input type="date" v-model="leaveForm.to_date" required />
            </div>
          </div>
          <div class="form-group">
            <label>Reason</label>
            <textarea v-model="leaveForm.reason" rows="3" placeholder="Reason for leave..." required></textarea>
          </div>
          <button type="submit" class="btn-primary" :disabled="leaveStore.isLoading">
            {{ leaveStore.isLoading ? 'Submitting...' : 'Apply Leave' }}
          </button>
        </form>
      </div>
    </div>

    <!-- My Leaves Tab -->
    <div v-if="activeTab === 'my'" class="tab-content">
      <div v-if="leaveStore.myLeaves.length === 0" class="empty-state">
        <p>No leave requests found.</p>
      </div>
      <div v-else class="leaves-list">
        <LeaveCard
          v-for="leave in leaveStore.myLeaves"
          :key="leave.id"
          :leave="leave"
          :show-actions="false"
          :show-cancel="leave.status === 'pending'"
          @cancel="handleCancel(leave.id)"
        />
      </div>
    </div>

    <!-- Pending Approvals Tab -->
    <div v-if="activeTab === 'pending'" class="tab-content">
      <div v-if="leaveStore.pendingLeaves.length === 0" class="empty-state">
        <p>No pending leave requests.</p>
      </div>
      <div v-else class="leaves-list">
        <LeaveCard
          v-for="leave in leaveStore.pendingLeaves"
          :key="leave.id"
          :leave="leave"
          :show-actions="true"
          @approve="handleApprove(leave.id)"
          @reject="handleReject(leave.id)"
        />
      </div>
    </div>

    <!-- All Leaves Tab -->
    <div v-if="activeTab === 'all'" class="tab-content">
      <div v-if="leaveStore.allLeaves.length === 0" class="empty-state">
        <p>No leave records found.</p>
      </div>
      <div v-else class="leaves-list">
        <LeaveCard
          v-for="leave in leaveStore.allLeaves"
          :key="leave.id"
          :leave="leave"
          :show-actions="leave.status === 'pending'"
          @approve="handleApprove(leave.id)"
          @reject="handleReject(leave.id)"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useLeaveStore } from '../stores/leave.js'
import { usePermissions } from '../composables/usePermissions.js'
import LeaveBalanceWidget from '../components/leave/LeaveBalanceWidget.vue'
import LeaveCard from '../components/leave/LeaveCard.vue'

const leaveStore = useLeaveStore()
const permissions = usePermissions()

const activeTab = ref('apply')
const leaveForm = ref({
  leave_type: '',
  from_date: '',
  to_date: '',
  reason: ''
})

const tabs = [
  { key: 'apply', label: 'Apply Leave', always: true },
  { key: 'my', label: 'My Leaves', always: true },
  { key: 'pending', label: 'Pending Approvals', managerOnly: true },
  { key: 'all', label: 'All Leaves', managerOnly: true }
]

const availableTabs = computed(() => {
  return tabs.filter(t => t.always || permissions.canViewAllLeaves())
})

async function handleApplyLeave() {
  const result = await leaveStore.applyLeave(leaveForm.value)
  if (result.success) {
    leaveForm.value = { leave_type: '', from_date: '', to_date: '', reason: '' }
    activeTab.value = 'my'
  }
}

async function handleApprove(id) {
  await leaveStore.approveLeave(id)
}

async function handleReject(id) {
  const reason = prompt('Reason for rejection:')
  if (reason !== null) {
    await leaveStore.rejectLeave(id, reason)
  }
}

async function handleCancel(id) {
  if (confirm('Are you sure you want to cancel this leave request?')) {
    await leaveStore.cancelLeave(id)
  }
}

onMounted(async () => {
  await Promise.all([
    leaveStore.fetchMyLeaves(),
    leaveStore.fetchBalance()
  ])
  if (permissions.canViewAllLeaves()) {
    await Promise.all([
      leaveStore.fetchPendingLeaves(),
      leaveStore.fetchAllLeaves()
    ])
  }
})
</script>

<style scoped>
.leave-page {
  max-width: 900px;
  margin: 0 auto;
}

.leave-page h1 {
  font-size: 1.5rem;
  color: #1e293b;
  margin-bottom: 20px;
}

.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 24px;
  border-bottom: 2px solid #e2e8f0;
  padding-bottom: 0;
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

.tab-btn:hover {
  color: #2563eb;
}

.tab-btn.active {
  color: #2563eb;
  border-bottom-color: #2563eb;
}

.tab-content {
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.form-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
}

.form-card h2 {
  font-size: 1.1rem;
  color: #334155;
  margin-bottom: 20px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-weight: 500;
  color: #334155;
  font-size: 0.85rem;
  margin-bottom: 6px;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 0.9rem;
  outline: none;
  transition: border-color 0.2s;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.form-group textarea {
  resize: vertical;
}

.btn-primary {
  padding: 10px 24px;
  background: #2563eb;
  color: white;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.95rem;
  transition: background 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.leaves-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #64748b;
  background: white;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}
</style>
