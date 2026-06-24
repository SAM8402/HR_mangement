import api from './axios.js'

export function markAttendance(notes = null) {
  return api.post('/attendance/mark', { notes })
}

export function getTodayStatus(userId = null) {
  const params = {}
  if (userId) params.user_id = userId
  return api.get('/attendance/today', { params })
}

export function getMonthlyReport(year, month, userId = null) {
  const params = { year, month }
  if (userId) params.user_id = userId
  return api.get('/attendance/report', { params })
}

export function getYearlyReport(year, userId = null) {
  const params = { year }
  if (userId) params.user_id = userId
  return api.get('/attendance/yearly', { params })
}
