import { computed } from 'vue'
import { useAuthStore } from '../stores/auth.js'

export function usePermissions() {
  const authStore = useAuthStore()

  const currentUserRole = computed(() => authStore.userRole)
  const isUserAdmin = computed(() => authStore.isAdmin)
  const isUserManager = computed(() => authStore.isManager)

  function hasRole(roles) {
    if (!roles || roles.length === 0) return true
    return roles.includes(currentUserRole.value)
  }

  function canApproveLeaves() {
    return ['admin', 'manager', 'hr'].includes(currentUserRole.value)
  }

  function canManageUsers() {
    return currentUserRole.value === 'admin'
  }

  function canManagePolicies() {
    return ['admin', 'hr'].includes(currentUserRole.value)
  }

  function canViewAllLeaves() {
    return ['admin', 'manager', 'hr'].includes(currentUserRole.value)
  }

  return {
    currentUserRole,
    isUserAdmin,
    isUserManager,
    hasRole,
    canApproveLeaves,
    canManageUsers,
    canManagePolicies,
    canViewAllLeaves
  }
}
