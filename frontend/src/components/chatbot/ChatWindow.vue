<template>
  <div class="chat-window" ref="windowRef">
    <div v-if="messages.length === 0" class="empty-chat">
      <div class="empty-icon">&#129302;</div>
      <p>Hi! I'm your HR assistant. Ask me anything about company policies, leave, or work updates.</p>
    </div>

    <MessageBubble
      v-for="(msg, index) in messages"
      :key="index"
      :message="msg"
    />

    <div v-if="streamingText" class="message-row assistant">
      <div class="message-bubble assistant">
        <span class="streaming-text">{{ streamingText }}</span>
        <span class="cursor-blink">|</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import MessageBubble from './MessageBubble.vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  streamingText: { type: String, default: '' }
})

const windowRef = ref(null)

async function scrollToBottom() {
  await nextTick()
  if (windowRef.value) {
    windowRef.value.scrollTop = windowRef.value.scrollHeight
  }
}

watch(() => props.messages.length, scrollToBottom)
watch(() => props.streamingText, scrollToBottom)
</script>

<style scoped>
.chat-window {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.empty-chat {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 200px;
  color: #94a3b8;
  text-align: center;
  padding: 40px;
}

.empty-icon {
  font-size: 2.5rem;
  margin-bottom: 12px;
}

.empty-chat p {
  max-width: 320px;
  font-size: 0.95rem;
  line-height: 1.5;
}

.message-row {
  display: flex;
}

.message-row.assistant {
  justify-content: flex-start;
}

.streaming-text {
  white-space: pre-wrap;
}

.cursor-blink {
  animation: blink 1s step-end infinite;
  color: #2563eb;
  font-weight: bold;
}

@keyframes blink {
  50% { opacity: 0; }
}
</style>
