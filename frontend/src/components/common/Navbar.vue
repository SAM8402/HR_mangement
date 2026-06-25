<template>
  <nav class="navbar">
    <div class="navbar-left">
      <button class="menu-toggle" @click="$emit('toggle-sidebar')">&#9776;</button>
      <span class="app-name">HR System</span>
    </div>
    <div class="navbar-right">
      <div class="user-profile" @click="goToProfile">
        <img v-if="authStore.user?.profile_image" :src="authStore.user.profile_image" class="avatar" />
        <div v-else class="avatar-placeholder">{{ authStore.user?.name?.charAt(0) || 'U' }}</div>
        <div class="user-info">
          <span class="user-name">{{ authStore.user?.name || 'User' }}</span>
          <span class="user-role">{{ authStore.userRole }}</span>
        </div>
      </div>
      <button class="logout-btn" @click="handleLogout">Logout</button>
    </div>
  </nav>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth.js'

defineEmits(['toggle-sidebar'])

const router = useRouter()
const authStore = useAuthStore()

function goToProfile() {
  router.push('/profile')
}

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 56px;
  background: white;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  z-index: 100;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.navbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.menu-toggle {
  display: none;
  background: none;
  font-size: 1.3rem;
  color: #475569;
  padding: 4px;
}

@media (max-width: 768px) {
  .menu-toggle { display: block; }
}

.app-name {
  font-size: 1.1rem;
  font-weight: 700;
  color: #2563eb;
}

.navbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;
  transition: background 0.2s;
}

.user-profile:hover {
  background: #f1f5f9;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  object-fit: cover;
}

.avatar-placeholder {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #2563eb;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  font-weight: 600;
}

.user-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.user-name {
  font-size: 0.85rem;
  font-weight: 500;
  color: #1e293b;
}

.user-role {
  font-size: 0.7rem;
  color: #64748b;
  text-transform: capitalize;
}

.logout-btn {
  padding: 6px 14px;
  background: #f1f5f9;
  color: #475569;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 500;
  transition: all 0.2s;
}

.logout-btn:hover {
  background: #fee2e2;
  color: #dc2626;
}
</style>
