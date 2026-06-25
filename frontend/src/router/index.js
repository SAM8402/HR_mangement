import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../pages/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../pages/Dashboard.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/leave',
    name: 'Leave',
    component: () => import('../pages/LeavePage.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/work-updates',
    name: 'WorkUpdates',
    component: () => import('../pages/WorkUpdates.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/policies',
    name: 'Policies',
    component: () => import('../pages/PoliciesPage.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/users',
    name: 'Users',
    component: () => import('../pages/UsersPage.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('../pages/ProfilePage.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('../pages/ChatPage.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/attendance',
    name: 'Attendance',
    component: () => import('../pages/EmployeeAttendance.vue'),
    meta: { requiresAuth: true, requiresManagerOrAdmin: true }
  },
  {
    path: '/evaluation',
    name: 'Evaluation',
    component: () => import('../pages/EvalDashboard.vue'),
    meta: { requiresAuth: true, requiresManagerOrAdmin: true }
  },
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('hr_token')

  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/dashboard')
  } else if (to.meta.requiresAdmin) {
    const userStr = localStorage.getItem('hr_user')
    let user = null
    try {
      user = userStr ? JSON.parse(userStr) : null
    } catch {
      user = null
    }
    if (!user || user.role !== 'admin') {
      next('/dashboard')
    } else {
      next()
    }
  } else if (to.meta.requiresManagerOrAdmin) {
    const userStr = localStorage.getItem('hr_user')
    let user = null
    try {
      user = userStr ? JSON.parse(userStr) : null
    } catch {
      user = null
    }
    if (!user || !['admin', 'manager', 'hr'].includes(user.role)) {
      next('/dashboard')
    } else {
      next()
    }
  } else {
    next()
  }
})

export default router
