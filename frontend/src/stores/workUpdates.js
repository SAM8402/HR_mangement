import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as workApi from '../api/workUpdates.js'

export const useWorkUpdateStore = defineStore('workUpdates', () => {
  const myUpdates = ref([])
  const allUpdates = ref([])
  const isLoading = ref(false)
  const monthlyUpdates = ref([])

  async function createUpdate(data) {
    isLoading.value = true
    try {
      await workApi.createUpdate(data)
      await fetchMyUpdates()
      return { success: true }
    } catch (err) {
      return {
        success: false,
        message: err.response?.data?.detail || 'Failed to create update'
      }
    } finally {
      isLoading.value = false
    }
  }

  async function fetchMyUpdates() {
    isLoading.value = true
    try {
      const res = await workApi.getMyUpdates()
      myUpdates.value = res.data
    } catch {
      myUpdates.value = []
    } finally {
      isLoading.value = false
    }
  }

  async function fetchMonthlyUpdates(year, month, userId) {
    try {
      let res
      if (userId) {
        res = await workApi.getAllUpdates({ user_id: userId, year, month })
      } else {
        res = await workApi.getMyUpdates({ year, month })
      }
      monthlyUpdates.value = res.data
      return res.data
    } catch {
      monthlyUpdates.value = []
      return null
    }
  }

  async function fetchAllUpdates(params) {
    isLoading.value = true
    try {
      const res = await workApi.getAllUpdates(params)
      allUpdates.value = res.data
    } catch {
      allUpdates.value = []
    } finally {
      isLoading.value = false
    }
  }

  async function updateUpdate(id, data) {
    isLoading.value = true
    try {
      await workApi.updateUpdate(id, data)
      await fetchMyUpdates()
      return { success: true }
    } catch (err) {
      return {
        success: false,
        message: err.response?.data?.detail || 'Failed to update'
      }
    } finally {
      isLoading.value = false
    }
  }

  async function deleteUpdate(id) {
    try {
      await workApi.deleteUpdate(id)
      myUpdates.value = myUpdates.value.filter(u => u.id !== id)
      allUpdates.value = allUpdates.value.filter(u => u.id !== id)
      return { success: true }
    } catch (err) {
      return {
        success: false,
        message: err.response?.data?.detail || 'Failed to delete'
      }
    }
  }

  return {
    myUpdates,
    allUpdates,
    isLoading,
    monthlyUpdates,
    createUpdate,
    fetchMyUpdates,
    fetchMonthlyUpdates,
    fetchAllUpdates,
    updateUpdate,
    deleteUpdate
  }
})
