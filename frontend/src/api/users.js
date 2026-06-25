import api from './axios.js'

export function getUsers(params) {
  return api.get('/users', { params })
}

export function getUser(id) {
  return api.get(`/users/${id}`)
}

export function createUser(data) {
  return api.post('/users', data)
}

export function updateUser(id, data) {
  return api.patch(`/users/${id}`, data)
}

export function deleteUser(id) {
  return api.delete(`/users/${id}`)
}

export function updateProfileImage(id, data) {
  return api.patch(`/users/${id}/profile-image`, data)
}
