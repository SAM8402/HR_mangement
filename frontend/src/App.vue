<template>
  <div class="app-root">
    <template v-if="authStore.isAuthenticated">
      <Navbar @toggle-sidebar="sidebarOpen = !sidebarOpen" />
      <div class="app-body">
        <Sidebar :open="sidebarOpen" :collapsed="sidebarCollapsed" @close="sidebarOpen = false" @toggle="sidebarCollapsed = !sidebarCollapsed" />
        <main class="main-content" :style="{ marginLeft: authStore.isAuthenticated ? sidebarWidth + 'px' : '0' }">
          <router-view />
        </main>
      </div>
    </template>
    <template v-else>
      <router-view />
    </template>
    <Toast />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from './stores/auth.js'
import Navbar from './components/common/Navbar.vue'
import Sidebar from './components/common/Sidebar.vue'
import Toast from './components/common/Toast.vue'

const authStore = useAuthStore()
const route = useRoute()
const sidebarOpen = ref(true)
const sidebarCollapsed = ref(false)

const sidebarWidth = computed(() => sidebarCollapsed.value ? 64 : 240)

watch(() => route.path, () => {
  if (window.innerWidth < 768) {
    sidebarOpen.value = false
  }
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f8fafc;
  color: #1e293b;
  line-height: 1.5;
}

a {
  text-decoration: none;
  color: inherit;
}

button {
  cursor: pointer;
  border: none;
  font-family: inherit;
}

input, textarea, select {
  font-family: inherit;
  font-size: 0.95rem;
}

.app-root {
  min-height: 100vh;
}

.app-body {
  display: flex;
  padding-top: 56px;
  min-height: calc(100vh - 56px);
}

.main-content {
  flex: 1;
  padding: 24px;
  transition: margin-left 0.3s;
}

@media (max-width: 768px) {
  .main-content {
    margin-left: 0 !important;
    padding: 16px;
  }
}
</style>
