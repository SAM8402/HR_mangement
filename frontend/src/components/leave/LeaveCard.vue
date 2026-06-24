<template>
  <div class="leave-card">
    <div class="card-header">
      <div class="card-type">
        <span class="type-icon">&#128197;</span>
        <span class="type-name">{{ formatType(leave.leave_type) }}</span>
      </div>
      <span :class="['status-badge', leave.status]">{{ leave.status }}</span>
    </div>

    <div class="card-body">
      <div class="card-dates">
        <span>{{ formatDate(leave.start_date) }} - {{ formatDate(leave.end_date) }}</span>
        <span class="days-count">{{ calculateDays }} day(s)</span>
      </div>
      <p v-if="leave.reason" class="card-reason">{{ leave.reason }}</p>
      <p v-if="leave.user_name" class="card-user">Requested by: {{ leave.user_name }}</p>
      <p v-if="leave.rejection_reason" class="rejection-reason">
        Rejection reason: {{ leave.rejection_reason }}
      </p>
    </div>

    <div v-if="showActions || showCancel" class="card-actions">
      <button v-if="showActions" class="btn-approve" @click="$emit('approve')">Approve</button>
      <button v-if="showActions" class="btn-reject" @click="$emit('reject')">Reject</button>
      <button v-if="showCancel" class="btn-cancel" @click="$emit('cancel')">Cancel</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  leave: { type: Object, required: true },
  showActions: { type: Boolean, default: false },
  showCancel: { type: Boolean, default: false }
})

defineEmits(['approve', 'reject', 'cancel'])

function formatType(type) {
  const types = {
    annual: 'Annual',
    sick: 'Sick',
    personal: 'Personal',
    maternity: 'Maternity',
    paternity: 'Paternity',
    unpaid: 'Unpaid'
  }
  return types[type] || type
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric'
  })
}

const calculateDays = computed(() => {
  if (!props.leave.start_date || !props.leave.end_date) return 0
  const start = new Date(props.leave.start_date)
  const end = new Date(props.leave.end_date)
  const diff = Math.ceil((end - start) / (1000 * 60 * 60 * 24)) + 1
  return diff > 0 ? diff : 0
})
</script>

<style scoped>
.leave-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 16px;
  transition: box-shadow 0.2s;
}

.leave-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.card-type {
  display: flex;
  align-items: center;
  gap: 8px;
}

.type-icon { font-size: 1.1rem; }

.type-name {
  font-weight: 600;
  color: #1e293b;
  font-size: 0.95rem;
}

.status-badge {
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: capitalize;
}

.status-badge.pending { background: #fef3c7; color: #92400e; }
.status-badge.approved { background: #d1fae5; color: #065f46; }
.status-badge.rejected { background: #fef2f2; color: #991b1b; }
.status-badge.cancelled { background: #f1f5f9; color: #475569; }

.card-body {
  margin-bottom: 12px;
}

.card-dates {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
  color: #475569;
  margin-bottom: 6px;
}

.days-count {
  font-weight: 500;
  color: #2563eb;
}

.card-reason {
  font-size: 0.85rem;
  color: #64748b;
  margin-top: 6px;
}

.card-user {
  font-size: 0.8rem;
  color: #94a3b8;
  margin-top: 4px;
}

.rejection-reason {
  font-size: 0.8rem;
  color: #dc2626;
  margin-top: 4px;
  font-style: italic;
}

.card-actions {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid #f1f5f9;
}

.btn-approve {
  padding: 6px 14px;
  background: #d1fae5;
  color: #065f46;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  transition: background 0.2s;
}

.btn-approve:hover { background: #a7f3d0; }

.btn-reject {
  padding: 6px 14px;
  background: #fef2f2;
  color: #991b1b;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  transition: background 0.2s;
}

.btn-reject:hover { background: #fecaca; }

.btn-cancel {
  padding: 6px 14px;
  background: #f1f5f9;
  color: #475569;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  transition: background 0.2s;
}

.btn-cancel:hover { background: #e2e8f0; }
</style>
