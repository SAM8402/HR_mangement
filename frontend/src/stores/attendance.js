import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as attendanceApi from '../api/attendance.js'
import * as usersApi from '../api/users.js'

export const useAttendanceStore = defineStore('attendance', () => {
  const todayStatus = ref(null)
  const monthlyRecords = ref([])
  const monthlyStats = ref({
    total_present: 0,
    total_absent: 0,
    total_late: 0,
    total_half_day: 0,
    total_wfh: 0,
  })
  const yearlyRecords = ref([])
  const yearlyStats = ref({
    total_present: 0,
    total_absent: 0,
    total_late: 0,
    total_half_day: 0,
    total_wfh: 0,
  })
  const selectedUserId = ref(null)
  const availableUsers = ref([])

  const userId = selectedUserId

  async function fetchUsers() {
    try {
      const res = await usersApi.getUsers()
      availableUsers.value = res.data.users || []
    } catch {
      availableUsers.value = []
    }
  }

  async function markAttendance(notes = null) {
    try {
      const res = await attendanceApi.markAttendance(notes)
      todayStatus.value = res.data
      return res.data
    } catch {
      return null
    }
  }

  async function fetchTodayStatus() {
    try {
      const res = await attendanceApi.getTodayStatus(selectedUserId.value)
      todayStatus.value = res.data
      return res.data
    } catch {
      todayStatus.value = null
      return null
    }
  }

  async function fetchMonthlyReport(year, month) {
    try {
      const res = await attendanceApi.getMonthlyReport(year, month, selectedUserId.value)
      monthlyRecords.value = res.data.records || []
      monthlyStats.value = {
        total_present: res.data.total_present || 0,
        total_absent: res.data.total_absent || 0,
        total_late: res.data.total_late || 0,
        total_half_day: res.data.total_half_day || 0,
        total_wfh: res.data.total_wfh || 0,
      }
      return res.data
    } catch {
      monthlyRecords.value = []
      return null
    }
  }

  async function fetchYearlyReport(year) {
    try {
      const res = await attendanceApi.getYearlyReport(year, selectedUserId.value)
      yearlyRecords.value = res.data.records || []
      yearlyStats.value = {
        total_present: res.data.total_present || 0,
        total_absent: res.data.total_absent || 0,
        total_late: res.data.total_late || 0,
        total_half_day: res.data.total_half_day || 0,
        total_wfh: res.data.total_wfh || 0,
      }
      return res.data
    } catch {
      yearlyRecords.value = []
      return null
    }
  }

  return {
    todayStatus,
    monthlyRecords,
    monthlyStats,
    yearlyRecords,
    yearlyStats,
    selectedUserId,
    availableUsers,
    fetchUsers,
    markAttendance,
    fetchTodayStatus,
    fetchMonthlyReport,
    fetchYearlyReport,
  }
})
