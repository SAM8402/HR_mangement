import api from './axios.js'

export function applyLeave(data) {
  return api.post('/leaves', data)
}

export function getMyLeaves() {
  return api.get('/leaves/my')
}

export function getBalance() {
  return api.get('/leaves/balance')
}

export function getPendingLeaves() {
  return api.get('/leaves/pending')
}

export function getAllLeaves(params) {
  return api.get('/leaves', { params })
}

export function approveLeave(id) {
  return api.post(`/leaves/${id}/approve`)
}

export function rejectLeave(id, reason) {
  return api.post(`/leaves/${id}/reject`, { reason })
}

export function cancelLeave(id) {
  return api.post(`/leaves/${id}/cancel`)
}
