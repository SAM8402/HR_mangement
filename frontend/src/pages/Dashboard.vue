<template>
  <div class="dashboard">
    <div class="welcome-section">
      <h1>Welcome back, {{ authStore.user?.name || 'User' }}!</h1>
      <p class="role-badge">{{ authStore.userRole }}</p>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon blue">
          <span>&#128197;</span>
        </div>
        <div class="stat-info">
          <h3>Leave Balance</h3>
          <p class="stat-value">{{ leaveBalance }} days</p>
        </div>
      </div>

      <div v-if="permissions.canApproveLeaves()" class="stat-card">
        <div class="stat-icon amber">
          <span>&#9200;</span>
        </div>
        <div class="stat-info">
          <h3>Pending Approvals</h3>
          <p class="stat-value">{{ pendingCount }}</p>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon green">
          <span>&#128196;</span>
        </div>
        <div class="stat-info">
          <h3>Work Updates</h3>
          <p class="stat-value">{{ updateCount }}</p>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon purple">
          <span>&#128172;</span>
        </div>
        <div class="stat-info">
          <h3>AI Assistant</h3>
          <p class="stat-value">Ready</p>
        </div>
      </div>
    </div>

    <div class="quick-actions">
      <h2>Quick Actions</h2>
      <div class="actions-grid">
        <router-link to="/leave" class="action-btn">
          <span class="action-icon">&#128197;</span>
          <span>Apply Leave</span>
        </router-link>
        <router-link to="/work-updates" class="action-btn">
          <span class="action-icon">&#128221;</span>
          <span>Add Work Update</span>
        </router-link>
        <router-link to="/chat" class="action-btn">
          <span class="action-icon">&#129302;</span>
          <span>Open Chatbot</span>
        </router-link>
        <router-link to="/policies" class="action-btn">
          <span class="action-icon">&#128220;</span>
          <span>View Policies</span>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useAuthStore } from '../stores/auth.js'
import { useLeaveStore } from '../stores/leave.js'
import { useWorkUpdateStore } from '../stores/workUpdates.js'
import { usePermissions } from '../composables/usePermissions.js'

const authStore = useAuthStore()
const leaveStore = useLeaveStore()
const workUpdateStore = useWorkUpdateStore()
const permissions = usePermissions()

const pendingCount = ref(0)
const updateCount = ref(0)

const leaveBalance = computed(() => {
  return leaveStore.balance.reduce((sum, b) => sum + (b.remaining || 0), 0)
})

onMounted(async () => {
  await Promise.all([
    leaveStore.fetchBalance(),
    leaveStore.fetchMyLeaves(),
    workUpdateStore.fetchMyUpdates()
  ])

  if (permissions.canApproveLeaves()) {
    await leaveStore.fetchPendingLeaves()
    pendingCount.value = leaveStore.pendingLeaves.length
  }

  updateCount.value = workUpdateStore.myUpdates.length
})
</script>

<style scoped>
.dashboard {
  max-width: 1000px;
  margin: 0 auto;
}

.welcome-section {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 32px;
}

.welcome-section h1 {
  font-size: 1.5rem;
  color: #1e293b;
}

.role-badge {
  background: #dbeafe;
  color: #2563eb;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 500;
  text-transform: capitalize;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 40px;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.3rem;
}

.stat-icon.blue { background: #dbeafe; }
.stat-icon.amber { background: #fef3c7; }
.stat-icon.green { background: #d1fae5; }
.stat-icon.purple { background: #ede9fe; }

.stat-info h3 {
  font-size: 0.8rem;
  color: #64748b;
  font-weight: 500;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 1.4rem;
  font-weight: 700;
  color: #1e293b;
}

.quick-actions h2 {
  font-size: 1.1rem;
  color: #334155;
  margin-bottom: 16px;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}

.action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 24px 16px;
  background: white;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: all 0.2s;
  font-weight: 500;
  color: #334155;
}

.action-btn:hover {
  border-color: #2563eb;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.1);
  transform: translateY(-2px);
}

.action-icon {
  font-size: 1.5rem;
}
</style>
