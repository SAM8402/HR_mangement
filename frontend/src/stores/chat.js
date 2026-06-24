import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as chatApi from '../api/chat.js'

export const useChatStore = defineStore('chat', () => {
  const messages = ref([])
  const isLoading = ref(false)
  const streamingText = ref('')

  function addUserMessage(text) {
    messages.value.push({
      role: 'user',
      content: text,
      timestamp: new Date().toISOString()
    })
  }

  function addBotMessage(text, citations = []) {
    messages.value.push({
      role: 'assistant',
      content: text,
      citations: citations,
      timestamp: new Date().toISOString(),
      feedbackSubmitted: null, // 'up' or 'down' or null
    })
  }

  function setStreamingText(text) {
    streamingText.value = text
  }

  function finalizeStream() {
    if (streamingText.value) {
      addBotMessage(streamingText.value)
      streamingText.value = ''
    }
  }

  async function sendMessage(query) {
    addUserMessage(query)
    isLoading.value = true
    streamingText.value = ''

    try {
      const token = localStorage.getItem('hr_token')
      const escQuery = encodeURIComponent(query)
      
      // Determine the API base URL (falls back to local if not structured)
      const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api'
      const url = `${baseUrl}/chat/stream?query=${escQuery}&token=${token}`
      
      const eventSource = new EventSource(url)

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.done) {
            eventSource.close()
            addBotMessage(streamingText.value, data.citations || [])
            streamingText.value = ''
            isLoading.value = false
          } else {
            streamingText.value += data.content
          }
        } catch (e) {
          console.error('SSE parsing error', e)
        }
      }

      eventSource.onerror = (err) => {
        eventSource.close()
        // If we streamed some response, finalize it, else show error
        if (streamingText.value) {
          addBotMessage(streamingText.value)
        } else {
          addBotMessage('Sorry, something went wrong with the streaming assistant. Please try again.')
        }
        streamingText.value = ''
        isLoading.value = false
      }
    } catch (err) {
      addBotMessage('Sorry, something went wrong. Please try again.')
      isLoading.value = false
    }
  }

  async function fetchHistory() {
    try {
      const res = await chatApi.getChatHistory()
      // History response has format: { history: [ { role, content }, ... ] }
      const historyList = res.data.history || res.data || []
      messages.value = historyList.map(msg => ({
        role: msg.role,
        content: msg.content,
        citations: msg.citations || [],
        timestamp: msg.timestamp || new Date().toISOString(),
        feedbackSubmitted: msg.feedback_submitted || null
      }))
    } catch (err) {
      messages.value = []
    }
  }

  async function clearHistory() {
    try {
      await chatApi.clearChatHistory()
      messages.value = []
    } catch {
      // ignore
    }
  }

  return {
    messages,
    isLoading,
    streamingText,
    addUserMessage,
    addBotMessage,
    setStreamingText,
    finalizeStream,
    sendMessage,
    fetchHistory,
    clearHistory
  }
})
