import api from './axios.js'

export function createUpdate(data) {
  return api.post('/work-updates', data)
}

export function getMyUpdates(params = {}) {
  return api.get('/work-updates/my', { params })
}

export function getAllUpdates(params) {
  return api.get('/work-updates/all', { params })
}

export function getUpdate(id) {
  return api.get(`/work-updates/${id}`)
}

export function updateUpdate(id, data) {
  return api.patch(`/work-updates/${id}`, data)
}

export function deleteUpdate(id) {
  return api.delete(`/work-updates/${id}`)
}
