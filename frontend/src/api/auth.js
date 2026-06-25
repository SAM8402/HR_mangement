import api from './axios.js'

export function login(email, password) {
  return api.post('/auth/login', { email, password })
}

export function logout() {
  return api.post('/auth/logout')
}

export function refreshToken(refreshToken) {
  return api.post('/auth/refresh', { refresh_token: refreshToken })
}

export function getMe() {
  return api.get('/auth/me')
}

export function changePassword(data) {
  return api.post('/auth/change-password', data)
}
