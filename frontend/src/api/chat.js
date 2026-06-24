import api from './axios.js'

export function sendMessage(query, sessionId) {
  return api.post('/chat', { query, session_id: sessionId || null })
}

export function getChatHistory(sessionId) {
  const params = sessionId ? { session_id: sessionId } : {}
  return api.get('/chat/history', { params })
}

export function clearChatHistory(sessionId) {
  const params = sessionId ? { session_id: sessionId } : {}
  return api.delete('/chat/history', { params })
}

export function submitFeedback(data) {
  return api.post('/chat/feedback', data)
}

export function getEvaluationMetrics() {
  return api.get('/chat/evaluation/metrics')
}

export function getSessions() {
  return api.get('/chat/sessions')
}

export function createSession(title) {
  return api.post('/chat/sessions', null, { params: { title: title || 'New Chat' } })
}

export function deleteSession(id) {
  return api.delete(`/chat/sessions/${id}`)
}

export function renameSession(id, title) {
  return api.put(`/chat/sessions/${id}`, { title })
}
