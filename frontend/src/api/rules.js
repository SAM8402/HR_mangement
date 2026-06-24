import api from './axios.js'

export function getRules() {
  return api.get('/rules')
}

export function createRule(data) {
  return api.post('/rules', data)
}

export function updateRule(id, data) {
  return api.patch(`/rules/${id}`, data)
}

export function deleteRule(id) {
  return api.delete(`/rules/${id}`)
}

export function uploadRuleDoc(file) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/rules/upload-doc', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function getRuleDocs() {
  return api.get('/docs/rules')
}

export function getRuleDoc(filename) {
  return api.get(`/docs/rules/${encodeURIComponent(filename)}`, { responseType: 'blob' })
}

export function uploadRuleDocFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/docs/rules/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function deleteRuleDoc(filename) {
  return api.delete(`/docs/rules/${encodeURIComponent(filename)}`)
}
