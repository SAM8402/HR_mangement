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

      <div class="stat-card">
        <div class="stat-icon cyan">
          <span>&#9201;</span>
        </div>
        <div class="stat-info">
          <h3>Attendance</h3>
          <AttendanceOverview />
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

    <div class="attendance-section">
    <div class="attendance-header">
        <h2>My Attendance</h2>
        <button class="checkin-btn" @click="handleCheckIn">
          {{ todayStatus?.check_in ? 'Check Out' : 'Check In' }}
        </button>
      </div>
      <div class="stats-row">
        <div class="stat-chip present">Present: {{ monthlyStats.total_present }}</div>
        <div class="stat-chip late">Late: {{ monthlyStats.total_late }}</div>
        <div class="stat-chip absent">Absent: {{ monthlyStats.total_absent }}</div>
        <div class="stat-chip half-day">Half Day: {{ monthlyStats.total_half_day }}</div>
        <div class="stat-chip wfh">WFH: {{ monthlyStats.total_wfh }}</div>
        <div class="stat-chip total">Total: {{ monthTotal }}</div>
      </div>

      <div class="calendar-card">
        <div class="weekday-row">
          <span v-for="d in weekdays" :key="d">{{ d }}</span>
        </div>
        <div class="day-grid">
          <div
            v-for="day in calendarDays"
            :key="day.dateStr"
            class="day-cell"
            :class="[
              day.status ? 'status-' + day.status : (day.isCurrentMonth ? 'empty-day' : 'other-month'),
              { clickable: day.isCurrentMonth && day.dateStr }
            ]"
            @click="day.isCurrentMonth && day.dateStr && openWorkUpdates(day.dateStr)"
          >
            <span class="day-num">{{ day.num }}</span>
            <span v-if="day.status && day.status !== 'absent'" class="day-indicator">{{ day.status }}</span>
          </div>
        </div>
      </div>

      <div class="today-bar" v-if="todayStatus">
        Today: <strong>{{ todayStatus.status }}</strong>
        <template v-if="todayStatus.check_in">
          &nbsp;at {{ new Date(todayStatus.check_in).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) }}
        </template>
      </div>

      <Modal :show="showWorkModal" @close="showWorkModal = false">
        <template #title>Work Updates - {{ selectedDate }}</template>
        <div v-if="selectedDateUpdates.length === 0" class="empty-state">No work updates for this date.</div>
        <div v-for="wu in selectedDateUpdates" :key="wu.id" class="work-card">
          <h4>{{ wu.title }}</h4>
          <p>{{ wu.description }}</p>
          <div class="work-tags" v-if="wu.tags && wu.tags.length">
            <span v-for="t in wu.tags" :key="t">{{ t }}</span>
          </div>
        </div>
      </Modal>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../stores/auth.js'
import { useAttendanceStore } from '../stores/attendance.js'
import { useLeaveStore } from '../stores/leave.js'
import { useWorkUpdateStore } from '../stores/workUpdates.js'
import { usePermissions } from '../composables/usePermissions.js'
import AttendanceOverview from '../components/attendance/AttendanceOverview.vue'
import Modal from '../components/common/Modal.vue'

const authStore = useAuthStore()
const attendanceStore = useAttendanceStore()
const leaveStore = useLeaveStore()
const workUpdateStore = useWorkUpdateStore()
const permissions = usePermissions()

const now = new Date()
const year = ref(now.getFullYear())
const month = ref(now.getMonth() + 1)
const pendingCount = ref(0)
const updateCount = ref(0)
const showWorkModal = ref(false)
const selectedDate = ref('')

const selectedDateUpdates = computed(() => {
  if (!selectedDate.value) return []
  return workUpdateStore.myUpdates.filter(u => {
    const ud = u.date ? u.date.slice(0, 10) : ''
    return ud === selectedDate.value
  })
})

function openWorkUpdates(dateStr) {
  selectedDate.value = dateStr
  showWorkModal.value = true
}

const { monthlyRecords, monthlyStats, todayStatus } = storeToRefs(attendanceStore)

const leaveBalance = computed(() => {
  return leaveStore.balance.reduce((sum, b) => sum + (b.remaining || 0), 0)
})

const monthTotal = computed(() => {
  const s = monthlyStats.value
  return s.total_present + s.total_late + s.total_half_day + s.total_wfh
})

const monthNames = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
]
const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

const calendarDays = computed(() => {
  const days = []
  const firstDay = new Date(year.value, month.value - 1, 1)
  const daysInMonth = new Date(year.value, month.value, 0).getDate()
  const startPad = firstDay.getDay()

  const attMap = {}
  for (const r of monthlyRecords.value) {
    const key = r.date ? r.date.slice(0, 10) : ''
    if (key) attMap[key] = r
  }

  for (let p = 0; p < startPad; p++) {
    days.push({ num: '', dateStr: '', isCurrentMonth: false, status: null })
  }

  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${year.value}-${String(month.value).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    const att = attMap[dateStr]
    days.push({
      num: d,
      dateStr,
      isCurrentMonth: true,
      status: att ? att.status : null,
    })
  }
  return days
})

async function handleCheckIn() {
  await attendanceStore.markAttendance()
  await attendanceStore.fetchTodayStatus()
  await attendanceStore.fetchMonthlyReport(year.value, month.value)
}

onMounted(async () => {
  await Promise.all([
    leaveStore.fetchBalance(),
    leaveStore.fetchMyLeaves(),
    workUpdateStore.fetchMyUpdates(),
    attendanceStore.fetchTodayStatus(),
    attendanceStore.fetchMonthlyReport(year.value, month.value),
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
.stat-icon.cyan { background: #cffafe; }

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

.attendance-section {
  margin-top: 40px;
}
.attendance-section h2 {
  font-size: 1.1rem;
  color: #334155;
  margin-bottom: 16px;
}
.stats-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.stat-chip {
  padding: 5px 12px;
  border-radius: 20px;
  font-size: 0.78rem;
  font-weight: 600;
}
.stat-chip.present { background: #d1fae5; color: #065f46; }
.stat-chip.late { background: #fef3c7; color: #92400e; }
.stat-chip.absent { background: #fee2e2; color: #991b1b; }
.stat-chip.half-day { background: #ffedd5; color: #9a3412; }
.stat-chip.wfh { background: #ede9fe; color: #5b21b6; }
.stat-chip.total { background: #dbeafe; color: #1e40af; }
.calendar-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 16px;
}
.weekday-row {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
  margin-bottom: 8px;
  text-align: center;
}
.weekday-row span {
  font-size: 0.78rem;
  font-weight: 700;
  color: #64748b;
  padding: 4px 0;
}
.day-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}
.day-cell {
  min-height: 54px;
  border-radius: 8px;
  padding: 3px 5px;
  font-size: 0.75rem;
  font-weight: 500;
  color: #334155;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.day-cell.other-month { background: transparent; border-color: transparent; }
.day-cell.empty-day { background: #fafafa; border-color: #f1f5f9; color: #94a3b8; }
.day-cell.status-present { background: #d1fae5; border-color: #86efac; }
.day-cell.status-late { background: #fef3c7; border-color: #fcd34d; }
.day-cell.status-absent { background: #fee2e2; border-color: #fca5a5; }
.day-cell.status-wfh { background: #ede9fe; border-color: #c4b5fd; }
.day-cell.status-half_day { background: #ffedd5; border-color: #fdba74; }
.day-num { font-weight: 700; font-size: 0.85rem; }
.day-indicator { font-size: 0.65rem; text-transform: uppercase; color: #64748b; }
.today-bar {
  font-size: 0.85rem;
  color: #475569;
  padding: 8px 0;
}
.day-cell.clickable { cursor: pointer; }
.day-cell.clickable:hover { box-shadow: 0 0 0 2px #2563eb; }
.empty-state { text-align: center; color: #94a3b8; padding: 24px 0; font-size: 0.9rem; }
.work-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 10px;
}
.work-card h4 { font-size: 0.9rem; color: #1e293b; margin-bottom: 4px; }
.work-card p { font-size: 0.82rem; color: #475569; line-height: 1.4; }
.work-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px; }
.work-tags span {
  font-size: 0.7rem;
  background: #e0e7ff;
  color: #3730a3;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 600;
}
.attendance-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.attendance-header h2 {
  margin-bottom: 0;
}
.checkin-btn {
  padding: 8px 20px;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.85rem;
  cursor: pointer;
}
.checkin-btn:hover {
  background: #1d4ed8;
}
</style>
