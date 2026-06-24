import api from './axios.js'

export function getRoles() {
  return api.get('/roles')
}

export function createRole(data) {
  return api.post('/roles', data)
}

export function updateRole(id, data) {
  return api.patch(`/roles/${id}`, data)
}

export function deleteRole(id) {
  return api.delete(`/roles/${id}`)
}

export function uploadDoc(file) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/roles/upload-doc', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function getRoleDocs() {
  return api.get('/docs/roles')
}

export function getRoleDoc(filename) {
  return api.get(`/docs/roles/${encodeURIComponent(filename)}`, { responseType: 'blob' })
}

export function uploadRoleDocFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/docs/roles/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function deleteRoleDoc(filename) {
  return api.delete(`/docs/roles/${encodeURIComponent(filename)}`)
}
