import api from './axios.js'

export function getDepartments() {
  return api.get('/departments')
}
