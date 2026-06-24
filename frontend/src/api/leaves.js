import api from './axios.js'

export function applyLeave(data) {
  return api.post('/leaves/apply', data)
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
  return api.get('/leaves/all', { params })
}

export function approveLeave(id) {
  return api.patch(`/leaves/${id}/approve`)
}

export function rejectLeave(id, reason) {
  return api.patch(`/leaves/${id}/reject`, { rejection_reason: reason })
}

export function cancelLeave(id) {
  return api.delete(`/leaves/${id}/cancel`)
}
