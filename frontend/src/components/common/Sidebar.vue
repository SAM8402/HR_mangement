<template>
  <aside :class="['sidebar', { open, collapsed }]">
    <div class="sidebar-overlay" v-if="open" @click="$emit('close')"></div>
    <div class="sidebar-header">
      <span class="sidebar-logo" v-if="!collapsed">HRMS</span>
      <button class="collapse-btn" @click="$emit('toggle')" :title="collapsed ? 'Expand' : 'Collapse'">
        {{ collapsed ? '\u25B6' : '\u25C0' }}
      </button>
    </div>
    <nav class="sidebar-nav">
      <router-link
        v-for="item in filteredMenuItems"
        :key="item.path"
        :to="item.path"
        :class="['nav-item', { active: isActive(item.path) }]"
        @click="$emit('close')"
        :title="collapsed ? item.label : ''"
      >
        <span class="nav-icon" v-html="item.icon"></span>
        <span class="nav-label" v-if="!collapsed">{{ item.label }}</span>
      </router-link>
    </nav>
  </aside>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth.js'
import { usePermissions } from '../../composables/usePermissions.js'

defineProps({ open: Boolean, collapsed: Boolean })
defineEmits(['close', 'toggle'])

const route = useRoute()
const authStore = useAuthStore()
const permissions = usePermissions()

const menuItems = [
  { path: '/dashboard', label: 'Dashboard', icon: '&#127968;', requiresAuth: true },
  { path: '/leave', label: 'Leave', icon: '&#128197;', requiresAuth: true },
  { path: '/work-updates', label: 'Work Updates', icon: '&#128221;', requiresAuth: true },
  { path: '/policies', label: 'Policies', icon: '&#128220;', requiresAuth: true },
  { path: '/users', label: 'Users', icon: '&#128101;', requiresAuth: true, adminOnly: true },
  { path: '/chat', label: 'Chat', icon: '&#129302;', requiresAuth: true },
  { path: '/evaluation', label: 'Evaluation', icon: '&#128202;', requiresAuth: true, managerOrAdminOnly: true }
]

const filteredMenuItems = menuItems.filter(item => {
  if (item.adminOnly && !permissions.canManageUsers()) return false
  if (item.managerOrAdminOnly && !['admin', 'manager'].includes(permissions.currentUserRole.value)) return false
  return true
})

function isActive(path) {
  return route.path === path || route.path.startsWith(path + '/')
}
</script>

<style scoped>
.sidebar {
  position: fixed;
  top: 56px;
  left: 0;
  width: 240px;
  height: calc(100vh - 56px);
  background: white;
  border-right: 1px solid #e2e8f0;
  z-index: 90;
  transition: transform 0.3s, width 0.3s;
  overflow-y: auto;
  overflow-x: hidden;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.04);
}

.sidebar.collapsed {
  width: 64px;
}

@media (max-width: 768px) {
  .sidebar {
    transform: translateX(-100%);
    width: 240px;
  }
  .sidebar.open {
    transform: translateX(0);
  }
  .sidebar.collapsed {
    width: 240px;
  }
}

.sidebar-overlay {
  display: none;
}

@media (max-width: 768px) {
  .sidebar-overlay {
    display: block;
    position: fixed;
    top: 56px;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.4);
    z-index: 89;
  }
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 16px 8px;
  border-bottom: 1px solid #f1f5f9;
  margin-bottom: 4px;
}

.sidebar-logo {
  font-size: 1.1rem;
  font-weight: 800;
  color: #2563eb;
  letter-spacing: 0.5px;
}

.collapse-btn {
  background: #f1f5f9;
  border: none;
  border-radius: 6px;
  width: 28px;
  height: 28px;
  font-size: 0.7rem;
  color: #64748b;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.collapse-btn:hover {
  background: #e2e8f0;
  color: #1e293b;
}

@media (max-width: 768px) {
  .collapse-btn {
    display: none;
  }
}

.sidebar-nav {
  padding: 4px 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  color: #475569;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.15s;
  white-space: nowrap;
  overflow: hidden;
  position: relative;
  border-left: 3px solid transparent;
}

.nav-item:hover {
  background: #f1f5f9;
  color: #1e293b;
}

.nav-item:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: 2px;
}

.nav-item.active {
  background: #eff6ff;
  color: #2563eb;
  border-left-color: #2563eb;
  font-weight: 600;
}

.nav-icon {
  font-size: 1.2rem;
  width: 24px;
  text-align: center;
  flex-shrink: 0;
}

.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 10px 0;
}

.sidebar.collapsed .nav-icon {
  width: auto;
}
</style>
