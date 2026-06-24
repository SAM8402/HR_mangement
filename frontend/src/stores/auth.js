import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as authApi from '../api/auth.js'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('hr_token') || '')
  const refreshTokenValue = ref(localStorage.getItem('hr_refresh_token') || '')

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isManager = computed(() => ['admin', 'manager', 'hr'].includes(user.value?.role))
  const userRole = computed(() => user.value?.role || '')

  function setTokens(access, refresh) {
    token.value = access
    refreshTokenValue.value = refresh
    localStorage.setItem('hr_token', access)
    if (refresh) {
      localStorage.setItem('hr_refresh_token', refresh)
    }
  }

  function clearTokens() {
    token.value = ''
    refreshTokenValue.value = ''
    user.value = null
    localStorage.removeItem('hr_token')
    localStorage.removeItem('hr_refresh_token')
  }

  async function login(email, password) {
    try {
      const res = await authApi.login(email, password)
      const data = res.data
      setTokens(data.access_token, data.refresh_token)
      await fetchMe()
      return { success: true }
    } catch (err) {
      clearTokens()
      return {
        success: false,
        message: err.response?.data?.detail || 'Login failed'
      }
    }
  }

  async function fetchMe() {
    try {
      const res = await authApi.getMe()
      user.value = res.data
    } catch {
      clearTokens()
    }
  }

  async function logout() {
    try {
      await authApi.logout()
    } catch {
      // ignore
    }
    clearTokens()
  }

  async function refreshAccessToken() {
    try {
      const res = await authApi.refreshToken(refreshTokenValue.value)
      const data = res.data
      setTokens(data.access_token, data.refresh_token || refreshTokenValue.value)
      return true
    } catch {
      clearTokens()
      return false
    }
  }

  return {
    user,
    token,
    refreshToken: refreshTokenValue,
    isAuthenticated,
    isAdmin,
    isManager,
    userRole,
    login,
    logout,
    fetchMe,
    refreshAccessToken
  }
})
