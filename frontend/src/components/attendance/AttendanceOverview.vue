<template>
  <div class="attendance-overview">
    <div class="status-header">
      <span class="status-indicator" :class="statusClass"></span>
      <span class="status-text">{{ statusLabel }}</span>
    </div>
    <div v-if="checkIn" class="time-row">
      <span class="time-label">Check-in</span>
      <span class="time-value">{{ checkIn }}</span>
    </div>
    <div v-if="checkOut" class="time-row">
      <span class="time-label">Check-out</span>
      <span class="time-value">{{ checkOut }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAttendanceStore } from '../../stores/attendance.js'

const attendanceStore = useAttendanceStore()

const checkIn = computed(() => {
  if (!attendanceStore.todayStatus?.check_in) return null
  const d = new Date(attendanceStore.todayStatus.check_in)
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
})

const checkOut = computed(() => {
  if (!attendanceStore.todayStatus?.check_out) return null
  const d = new Date(attendanceStore.todayStatus.check_out)
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
})

const statusClass = computed(() => {
  const s = attendanceStore.todayStatus?.status
  if (s === 'present' || s === 'wfh') return 'green'
  if (s === 'late') return 'amber'
  if (s === 'absent') return 'red'
  return 'gray'
})

const statusLabel = computed(() => {
  const s = attendanceStore.todayStatus?.status
  if (!s || s === 'not_marked') return 'Not Marked'
  if (s === 'wfh') return 'Work from Home'
  return s.charAt(0).toUpperCase() + s.slice(1)
})
</script>

<style scoped>
.attendance-overview {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.status-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
.status-indicator.green { background: #22c55e; }
.status-indicator.amber { background: #f59e0b; }
.status-indicator.red { background: #ef4444; }
.status-indicator.gray { background: #94a3b8; }
.status-text {
  font-size: 0.9rem;
  font-weight: 600;
  color: #1e293b;
}
.time-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
}
.time-label { color: #64748b; }
.time-value { color: #334155; font-weight: 500; }
</style>
