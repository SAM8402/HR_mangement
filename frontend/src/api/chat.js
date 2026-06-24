import api from './axios.js'

export function sendMessage(query) {
  return api.post('/chat', { query })
}

export function getChatHistory() {
  return api.get('/chat/history')
}

export function clearChatHistory() {
  return api.delete('/chat/history')
}

export function submitFeedback(data) {
  return api.post('/chat/feedback', data)
}

export function getEvaluationMetrics() {
  return api.get('/chat/evaluation/metrics')
}
