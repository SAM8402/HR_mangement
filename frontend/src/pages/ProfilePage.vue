<template>
  <div class="profile-page">
    <h1>My Profile</h1>

    <div class="profile-card">
      <div class="card-header">Profile Information</div>
      <div class="card-body">
        <div class="avatar-section">
          <div class="avatar-wrapper" @click="triggerFileInput">
            <img v-if="authStore.user?.profile_image" :src="authStore.user.profile_image" class="avatar-lg" />
            <div v-else class="avatar-placeholder-lg">{{ authStore.user?.name?.charAt(0) || 'U' }}</div>
            <div class="avatar-overlay"><span>Change</span></div>
          </div>
          <input ref="fileInput" type="file" accept="image/*" hidden @change="onImageChange" />
          <p v-if="imageStatus" :class="['status-msg', imageStatus.type]">{{ imageStatus.text }}</p>
        </div>
        <div class="detail-grid">
          <div class="detail-item">
            <label>Full Name</label>
            <span>{{ authStore.user?.name || '-' }}</span>
          </div>
          <div class="detail-item">
            <label>Email</label>
            <span>{{ authStore.user?.email || '-' }}</span>
          </div>
          <div class="detail-item">
            <label>Role</label>
            <span class="role-badge">{{ authStore.user?.role || '-' }}</span>
          </div>
          <div class="detail-item">
            <label>Department</label>
            <span>{{ authStore.user?.department || '-' }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="profile-card">
      <div class="card-header">Change Password</div>
      <div class="card-body">
        <form @submit.prevent="handleChangePassword" class="password-form">
          <div class="form-group">
            <label>Current Password</label>
            <input v-model="passwordForm.old_password" type="password" placeholder="Enter current password" required />
          </div>
          <div class="form-group">
            <label>New Password</label>
            <input v-model="passwordForm.new_password" type="password" placeholder="Min 6 characters" required minlength="6" />
          </div>
          <div class="form-group">
            <label>Confirm New Password</label>
            <input v-model="passwordForm.confirm_password" type="password" placeholder="Re-enter new password" required />
          </div>
          <p v-if="passwordStatus" :class="['status-msg', passwordStatus.type]">{{ passwordStatus.text }}</p>
          <button type="submit" class="btn-primary" :disabled="passwordSaving">
            {{ passwordSaving ? 'Updating...' : 'Update Password' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth.js'
import { updateProfileImage } from '../api/users.js'
import { changePassword } from '../api/auth.js'

const authStore = useAuthStore()
const fileInput = ref(null)
const imageStatus = ref(null)
const passwordSaving = ref(false)
const passwordStatus = ref(null)

const passwordForm = ref({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

function triggerFileInput() {
  fileInput.value?.click()
}

async function onImageChange(e) {
  const file = e.target.files[0]
  if (!file) return
  if (file.size > 2 * 1024 * 1024) {
    imageStatus.value = { type: 'error', text: 'Image must be under 2MB' }
    return
  }
  imageStatus.value = { type: 'info', text: 'Uploading...' }
  const reader = new FileReader()
  reader.onload = async () => {
    try {
      await updateProfileImage(authStore.user.id, { profile_image: reader.result })
      await authStore.fetchMe()
      imageStatus.value = { type: 'success', text: 'Profile image updated!' }
      setTimeout(() => { imageStatus.value = null }, 3000)
    } catch {
      imageStatus.value = { type: 'error', text: 'Failed to update profile image' }
    }
  }
  reader.readAsDataURL(file)
}

async function handleChangePassword() {
  passwordStatus.value = null
  if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
    passwordStatus.value = { type: 'error', text: 'New passwords do not match' }
    return
  }
  if (passwordForm.value.new_password.length < 6) {
    passwordStatus.value = { type: 'error', text: 'Password must be at least 6 characters' }
    return
  }
  passwordSaving.value = true
  try {
    await changePassword({
      old_password: passwordForm.value.old_password,
      new_password: passwordForm.value.new_password
    })
    passwordStatus.value = { type: 'success', text: 'Password updated successfully!' }
    passwordForm.value = { old_password: '', new_password: '', confirm_password: '' }
    setTimeout(() => { passwordStatus.value = null }, 3000)
  } catch (err) {
    const detail = err.response?.data?.detail || 'Failed to update password'
    passwordStatus.value = { type: 'error', text: detail }
  } finally {
    passwordSaving.value = false
  }
}
</script>

<style scoped>
.profile-page {
  max-width: 640px;
  margin: 0 auto;
}
h1 {
  font-size: 1.5rem;
  color: #1e293b;
  margin-bottom: 24px;
}
.profile-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  border: 1px solid #e2e8f0;
  margin-bottom: 20px;
  overflow: hidden;
}
.card-header {
  padding: 14px 20px;
  font-size: 0.95rem;
  font-weight: 600;
  color: #1e293b;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}
.card-body {
  padding: 20px;
}
.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 24px;
}
.avatar-wrapper {
  position: relative;
  cursor: pointer;
  border-radius: 50%;
  overflow: hidden;
}
.avatar-lg {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  object-fit: cover;
  border: 3px solid #e2e8f0;
}
.avatar-placeholder-lg {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: #2563eb;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.2rem;
  font-weight: 600;
  border: 3px solid #e2e8f0;
}
.avatar-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 0.8rem;
  font-weight: 500;
  opacity: 0;
  transition: opacity 0.2s;
}
.avatar-wrapper:hover .avatar-overlay { opacity: 1; }
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.detail-item label {
  display: block;
  font-size: 0.8rem;
  font-weight: 500;
  color: #64748b;
  margin-bottom: 2px;
}
.detail-item span {
  font-size: 0.95rem;
  color: #1e293b;
}
.role-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 0.8rem !important;
  background: #dbeafe;
  color: #2563eb;
  text-transform: capitalize;
}
.password-form {
  max-width: 400px;
}
.form-group {
  margin-bottom: 14px;
}
.form-group label {
  display: block;
  font-weight: 500;
  color: #334155;
  font-size: 0.85rem;
  margin-bottom: 4px;
}
.form-group input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.9rem;
  outline: none;
}
.form-group input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.1);
}
.status-msg {
  font-size: 0.85rem;
  margin-bottom: 12px;
  padding: 6px 10px;
  border-radius: 6px;
}
.status-msg.success { background: #d1fae5; color: #059669; }
.status-msg.error { background: #fef2f2; color: #dc2626; }
.status-msg.info { background: #dbeafe; color: #2563eb; }
.btn-primary {
  padding: 8px 20px;
  background: #2563eb;
  color: white;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.85rem;
  transition: background 0.2s;
}
.btn-primary:hover { background: #1d4ed8; }
.btn-primary:disabled { opacity: 0.7; cursor: not-allowed; }
</style>
