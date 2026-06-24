import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as leavesApi from '../api/leaves.js'

export const useLeaveStore = defineStore('leave', () => {
  const myLeaves = ref([])
  const pendingLeaves = ref([])
  const allLeaves = ref([])
  const balance = ref([])
  const isLoading = ref(false)

  async function applyLeave(data) {
    isLoading.value = true
    try {
      await leavesApi.applyLeave(data)
      await fetchMyLeaves()
      await fetchBalance()
      return { success: true }
    } catch (err) {
      return {
        success: false,
        message: err.response?.data?.detail || 'Failed to apply leave'
      }
    } finally {
      isLoading.value = false
    }
  }

  async function fetchMyLeaves() {
    isLoading.value = true
    try {
      const res = await leavesApi.getMyLeaves()
      myLeaves.value = res.data
    } catch {
      myLeaves.value = []
    } finally {
      isLoading.value = false
    }
  }

  async function fetchBalance() {
    try {
      const res = await leavesApi.getBalance()
      balance.value = (res.data || []).map(b => ({
        leave_type: b.leave_type_name,
        total: b.total_days,
        used: b.used_days,
        remaining: b.remaining_days,
      }))
    } catch {
      balance.value = []
    }
  }

  async function fetchPendingLeaves() {
    isLoading.value = true
    try {
      const res = await leavesApi.getPendingLeaves()
      pendingLeaves.value = res.data
    } catch {
      pendingLeaves.value = []
    } finally {
      isLoading.value = false
    }
  }

  async function fetchAllLeaves(params) {
    isLoading.value = true
    try {
      const res = await leavesApi.getAllLeaves(params)
      allLeaves.value = res.data
    } catch {
      allLeaves.value = []
    } finally {
      isLoading.value = false
    }
  }

  async function approveLeave(id) {
    try {
      await leavesApi.approveLeave(id)
      pendingLeaves.value = pendingLeaves.value.filter(l => l.id !== id)
      return { success: true }
    } catch (err) {
      return {
        success: false,
        message: err.response?.data?.detail || 'Failed to approve'
      }
    }
  }

  async function rejectLeave(id, reason) {
    try {
      await leavesApi.rejectLeave(id, reason)
      pendingLeaves.value = pendingLeaves.value.filter(l => l.id !== id)
      return { success: true }
    } catch (err) {
      return {
        success: false,
        message: err.response?.data?.detail || 'Failed to reject'
      }
    }
  }

  async function cancelLeave(id) {
    try {
      await leavesApi.cancelLeave(id)
      await fetchMyLeaves()
      return { success: true }
    } catch (err) {
      return {
        success: false,
        message: err.response?.data?.detail || 'Failed to cancel'
      }
    }
  }

  return {
    myLeaves,
    pendingLeaves,
    allLeaves,
    balance,
    isLoading,
    applyLeave,
    fetchMyLeaves,
    fetchBalance,
    fetchPendingLeaves,
    fetchAllLeaves,
    approveLeave,
    rejectLeave,
    cancelLeave
  }
})
