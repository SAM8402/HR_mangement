<template>
  <div class="balance-widget">
    <h3>Leave Balance</h3>
    <div v-if="leaveStore.balance.length === 0" class="empty">No balance data available.</div>
    <div v-else class="balance-grid">
      <div v-for="item in leaveStore.balance" :key="item.leave_type" class="balance-item">
        <div class="balance-header">
          <span class="balance-type">{{ formatType(item.leave_type) }}</span>
          <span class="balance-numbers">
            {{ item.used || 0 }} / {{ item.total || 0 }}
          </span>
        </div>
        <div class="progress-bar">
          <div
            class="progress-fill"
            :style="{ width: progressPercent(item) + '%' }"
            :class="progressColorClass(item)"
          ></div>
        </div>
        <div class="balance-footer">
          <span>Remaining: <strong>{{ (item.total || 0) - (item.used || 0) }}</strong></span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useLeaveStore } from '../../stores/leave.js'

const leaveStore = useLeaveStore()

function formatType(type) {
  const types = {
    annual: 'Annual Leave',
    sick: 'Sick Leave',
    personal: 'Personal Leave',
    maternity: 'Maternity Leave',
    paternity: 'Paternity Leave',
    unpaid: 'Unpaid Leave',
    casual: 'Casual Leave',
    earned: 'Earned Leave',
    paid: 'Paid Leave'
  }
  return types[type] || type
}

function progressPercent(item) {
  const total = item.total || 1
  const used = item.used || 0
  return Math.min((used / total) * 100, 100)
}

function progressColorClass(item) {
  const pct = progressPercent(item)
  if (pct >= 80) return 'danger'
  if (pct >= 50) return 'warning'
  return 'good'
}

onMounted(() => {
  if (leaveStore.balance.length === 0) {
    leaveStore.fetchBalance()
  }
})
</script>

<style scoped>
.balance-widget {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
  margin-bottom: 24px;
}

.balance-widget h3 {
  font-size: 0.95rem;
  color: #334155;
  margin-bottom: 16px;
}

.empty {
  color: #94a3b8;
  font-size: 0.9rem;
  text-align: center;
  padding: 12px;
}

.balance-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.balance-item {
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px;
  border: 1px solid #f1f5f9;
}

.balance-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.balance-type {
  font-size: 0.8rem;
  font-weight: 500;
  color: #475569;
}

.balance-numbers {
  font-size: 0.8rem;
  color: #64748b;
}

.progress-bar {
  height: 6px;
  background: #e2e8f0;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 6px;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s;
}

.progress-fill.good { background: #22c55e; }
.progress-fill.warning { background: #f59e0b; }
.progress-fill.danger { background: #ef4444; }

.balance-footer {
  font-size: 0.75rem;
  color: #64748b;
}
</style>
