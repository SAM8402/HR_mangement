<template>
  <div class="employee-attendance">
    <div class="page-header">
      <h1>{{ pageTitle }} Attendance</h1>
      <div class="header-controls">
        <select v-if="authStore.isManager" v-model="selectedUserId" class="employee-select">
          <option :value="null">My Attendance</option>
          <option v-for="u in attStore.availableUsers" :key="u.id" :value="u.id">{{ u.name }} ({{ u.role }})</option>
        </select>
        <div class="month-selector">
          <select v-model.number="year">
            <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}</option>
          </select>
          <select v-model.number="month">
            <option v-for="(m, i) in monthNames" :key="i" :value="i + 1">{{ m }}</option>
          </select>
        </div>
      </div>
    </div>

    <div class="stats-row">
      <div class="stat-chip present">Present: {{ attStore.monthlyStats.total_present }}</div>
      <div class="stat-chip late">Late: {{ attStore.monthlyStats.total_late }}</div>
      <div class="stat-chip absent">Absent: {{ attStore.monthlyStats.total_absent }}</div>
      <div class="stat-chip half-day">Half Day: {{ attStore.monthlyStats.total_half_day }}</div>
      <div class="stat-chip wfh">WFH: {{ attStore.monthlyStats.total_wfh }}</div>
      <div class="stat-chip total-m">Month Total: <strong>{{ monthTotal }}</strong></div>
      <div class="stat-chip total-y">Year Total: <strong>{{ yearTotal }}</strong></div>
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
          <span v-if="day.updateTitle" class="day-update" :title="day.updateTitle">{{ day.updateTitle }}</span>
          <span v-else-if="day.status && day.status !== 'absent'" class="day-indicator">{{ day.status }}</span>
        </div>
      </div>
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

    <div class="mark-today" v-if="!selectedUserId">
      <button class="btn-mark" :disabled="marking" @click="markToday">
        {{ marking ? 'Marking...' : "Mark Today's Attendance" }}
      </button>
      <span v-if="attStore.todayStatus" class="today-info">
        Today: <strong>{{ attStore.todayStatus.status }}</strong>
        <template v-if="attStore.todayStatus.check_in">
          &nbsp;at {{ new Date(attStore.todayStatus.check_in).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) }}
        </template>
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useAttendanceStore } from '../stores/attendance.js'
import { useWorkUpdateStore } from '../stores/workUpdates.js'
import { useAuthStore } from '../stores/auth.js'
import Modal from '../components/common/Modal.vue'

const attStore = useAttendanceStore()
const workStore = useWorkUpdateStore()
const authStore = useAuthStore()

const now = new Date()
const year = ref(now.getFullYear())
const month = ref(now.getMonth() + 1)
const marking = ref(false)

const { selectedUserId } = storeToRefs(attStore)

const pageTitle = computed(() => {
  if (!selectedUserId.value) return 'My'
  const u = attStore.availableUsers.find(x => x.id === selectedUserId.value)
  return u ? u.name : 'Employee'
})

const monthTotal = computed(() => {
  const s = attStore.monthlyStats
  return s.total_present + s.total_late + s.total_half_day + s.total_wfh
})

const yearTotal = computed(() => {
  const s = attStore.yearlyStats
  return s.total_present + s.total_late + s.total_half_day + s.total_wfh
})

const showWorkModal = ref(false)
const selectedDate = ref('')

const selectedDateUpdates = computed(() => {
  if (!selectedDate.value) return []
  return workStore.monthlyUpdates.filter(u => {
    const ud = u.date ? u.date.slice(0, 10) : ''
    return ud === selectedDate.value
  })
})

function openWorkUpdates(dateStr) {
  selectedDate.value = dateStr
  showWorkModal.value = true
}

const monthNames = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
]
const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

const yearOptions = computed(() => {
  const y = now.getFullYear()
  return [y - 2, y - 1, y, y + 1]
})

const calendarDays = computed(() => {
  const days = []
  const firstDay = new Date(year.value, month.value - 1, 1)
  const daysInMonth = new Date(year.value, month.value, 0).getDate()
  const startPad = firstDay.getDay()

  const attMap = {}
  for (const r of attStore.monthlyRecords) {
    const key = r.date ? r.date.slice(0, 10) : ''
    if (key) attMap[key] = r
  }

  const workMap = {}
  for (const u of workStore.monthlyUpdates) {
    const key = u.date ? u.date.slice(0, 10) : ''
    if (key) workMap[key] = u
  }

  for (let p = 0; p < startPad; p++) {
    days.push({ num: '', dateStr: '', isCurrentMonth: false, status: null, updateTitle: null })
  }

  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${year.value}-${String(month.value).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    const att = attMap[dateStr]
    const work = workMap[dateStr]
    days.push({
      num: d,
      dateStr,
      isCurrentMonth: true,
      status: att ? att.status : null,
      updateTitle: work ? work.title : null,
    })
  }

  return days
})

async function markToday() {
  marking.value = true
  await attStore.markAttendance()
  marking.value = false
  await attStore.fetchTodayStatus()
  await loadMonth()
}

async function loadMonth() {
  await Promise.all([
    attStore.fetchMonthlyReport(year.value, month.value),
    workStore.fetchMonthlyUpdates(year.value, month.value),
    attStore.fetchTodayStatus(),
  ])
}

async function loadYear() {
  await attStore.fetchYearlyReport(year.value)
}

watch([year, month], loadMonth)
watch(selectedUserId, () => {
  loadMonth()
  loadYear()
})

onMounted(async () => {
  if (!authStore.user) await authStore.fetchMe()
  if (authStore.isManager) {
    await attStore.fetchUsers()
  }
  await loadMonth()
  await loadYear()
})
</script>

<style scoped>
.employee-attendance {
  max-width: 760px;
  margin: 0 auto;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-header h1 { font-size: 1.4rem; color: #1e293b; }
.month-selector {
  display: flex;
  gap: 8px;
}
.month-selector select {
  padding: 6px 14px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 600;
  color: #1e293b;
  background: #fff;
  cursor: pointer;
}
.month-selector select:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}
.stats-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 20px;
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
.header-controls { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.employee-select { padding: 6px 14px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 0.85rem; color: #1e293b; background: #fff; cursor: pointer; }
.stat-chip.total-m { background: #dbeafe; color: #1e40af; }
.stat-chip.total-y { background: #e0e7ff; color: #3730a3; }

.calendar-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 20px;
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
  min-height: 64px;
  border-radius: 8px;
  padding: 4px 6px;
  font-size: 0.78rem;
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
.day-update {
  font-size: 0.62rem;
  line-height: 1.2;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  background: rgba(255,255,255,0.5);
  border-radius: 3px;
  padding: 0 3px;
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

.mark-today {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.btn-mark {
  padding: 8px 20px;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
}
.btn-mark:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-mark:hover:not(:disabled) { background: #1d4ed8; }
.today-info { font-size: 0.85rem; color: #475569; }
</style>
