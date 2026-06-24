import axios from 'axios'
import router from '../router/index.js'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('hr_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response && error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      const refreshToken = localStorage.getItem('hr_refresh_token')
      if (refreshToken) {
        try {
          const res = await axios.post('/api/auth/refresh', {
            refresh_token: refreshToken
          })
          const { access_token } = res.data
          localStorage.setItem('hr_token', access_token)
          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return api(originalRequest)
        } catch {
          localStorage.removeItem('hr_token')
          localStorage.removeItem('hr_refresh_token')
          router.push('/login')
        }
      } else {
        localStorage.removeItem('hr_token')
        router.push('/login')
      }
    }

    return Promise.reject(error)
  }
)

export default api
