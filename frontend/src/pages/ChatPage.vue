<template>
  <div class="chat-layout">
    <ChatHistorySidebar
      :sessions="chatStore.sessions"
      :current-id="chatStore.currentSessionId"
      @select-session="handleSelectSession"
      @new-session="handleNewSession"
      @delete-session="handleDeleteSession"
      @rename-session="handleRenameSession"
    />

    <div class="chat-page">
      <div class="chat-header">
        <h1>AI Assistant</h1>
        <button class="btn-clear" @click="handleClear">Clear Chat</button>
      </div>

      <div class="chat-container">
        <ChatWindow :messages="chatStore.messages" :streaming-text="chatStore.streamingText" />

        <div v-if="chatStore.isLoading" class="typing-indicator">
          <StreamingDot />
        </div>
      </div>

      <div class="chat-input-area">
        <form @submit.prevent="handleSend" class="input-form">
          <input
            v-model="message"
            type="text"
            placeholder="Ask me anything about company policies, leave, work updates..."
            :disabled="chatStore.isLoading"
            class="chat-input"
            ref="inputRef"
          />
          <button
            type="submit"
            class="send-btn"
            :disabled="!message.trim() || chatStore.isLoading"
          >
            &#10148;
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useChatStore } from '../stores/chat.js'
import ChatWindow from '../components/chatbot/ChatWindow.vue'
import StreamingDot from '../components/chatbot/StreamingDot.vue'
import ChatHistorySidebar from '../components/chatbot/ChatHistorySidebar.vue'

const chatStore = useChatStore()
const message = ref('')
const inputRef = ref(null)

async function handleSend() {
  const text = message.value.trim()
  if (!text || chatStore.isLoading) return
  message.value = ''
  await chatStore.sendMessage(text)
  inputRef.value?.focus()
}

function handleClear() {
  if (confirm('Clear current chat history?')) {
    chatStore.clearHistory()
  }
}

async function handleSelectSession(sessionId) {
  await chatStore.switchSession(sessionId)
}

async function handleNewSession() {
  await chatStore.createSession()
}

function handleDeleteSession(sessionId) {
  if (confirm('Delete this session?')) {
    chatStore.deleteSession(sessionId)
  }
}

function handleRenameSession(sessionId, title) {
  chatStore.renameSession(sessionId, title)
}

onMounted(async () => {
  await chatStore.refreshSessions()
  await chatStore.fetchHistory()
  inputRef.value?.focus()
})
</script>

<style scoped>
.chat-layout {
  display: flex;
  height: calc(100vh - 104px);
}

.chat-page {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  padding: 0 24px;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-top: 0;
}

.chat-header h1 {
  font-size: 1.5rem;
  color: #1e293b;
}

.btn-clear {
  padding: 6px 14px;
  background: #f1f5f9;
  color: #64748b;
  border-radius: 6px;
  font-size: 0.8rem;
  transition: all 0.2s;
}

.btn-clear:hover {
  background: #e2e8f0;
  color: #334155;
}

.chat-container {
  flex: 1;
  background: white;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  overflow-y: auto;
  padding: 20px;
  margin-bottom: 12px;
  min-height: 300px;
}

.typing-indicator {
  padding: 8px 0;
}

.chat-input-area {
  background: white;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  padding: 8px;
  margin-bottom: 16px;
}

.input-form {
  display: flex;
  gap: 8px;
}

.chat-input {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid transparent;
  border-radius: 8px;
  font-size: 0.95rem;
  outline: none;
  background: #f8fafc;
  transition: all 0.2s;
}

.chat-input:focus {
  border-color: #2563eb;
  background: white;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.chat-input:disabled {
  opacity: 0.7;
}

.send-btn {
  width: 44px;
  height: 44px;
  background: #2563eb;
  color: white;
  border-radius: 8px;
  font-size: 1.1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
