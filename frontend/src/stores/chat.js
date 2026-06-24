import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as chatApi from '../api/chat.js'

export const useChatStore = defineStore('chat', () => {
  const messages = ref([])
  const isLoading = ref(false)
  const streamingText = ref('')
  const sessions = ref([])
  const currentSessionId = ref(null)

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
      feedbackSubmitted: null,
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
      const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api'
      let url = `${baseUrl}/chat/stream?query=${escQuery}&token=${token}`
      if (currentSessionId.value) {
        url += `&session_id=${encodeURIComponent(currentSessionId.value)}`
      }

      const eventSource = new EventSource(url)

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.session_id) {
            currentSessionId.value = data.session_id
          }
          if (data.done) {
            eventSource.close()
            addBotMessage(streamingText.value, data.citations || [])
            streamingText.value = ''
            isLoading.value = false
            refreshSessions()
          } else {
            streamingText.value += data.content
          }
        } catch (e) {
          console.error('SSE parsing error', e)
        }
      }

      eventSource.onerror = (err) => {
        eventSource.close()
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
      const res = await chatApi.getChatHistory(currentSessionId.value)
      const historyList = res.data.history || res.data || []
      if (res.data.session_id) {
        currentSessionId.value = res.data.session_id
      }
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
      await chatApi.clearChatHistory(currentSessionId.value)
      messages.value = []
    } catch {
      // ignore
    }
  }

  async function refreshSessions() {
    try {
      const res = await chatApi.getSessions()
      sessions.value = res.data.sessions || []
    } catch {
      // ignore
    }
  }

  async function createSession(title) {
    try {
      const res = await chatApi.createSession(title)
      currentSessionId.value = res.data.session_id
      messages.value = []
      await refreshSessions()
      return res.data.session_id
    } catch {
      return null
    }
  }

  async function switchSession(sessionId) {
    currentSessionId.value = sessionId
    await fetchHistory()
  }

  async function deleteSession(sessionId) {
    try {
      await chatApi.deleteSession(sessionId)
      if (currentSessionId.value === sessionId) {
        currentSessionId.value = null
        messages.value = []
      }
      await refreshSessions()
    } catch {
      // ignore
    }
  }

  async function renameSession(sessionId, title) {
    try {
      await chatApi.renameSession(sessionId, title)
      await refreshSessions()
    } catch {
      // ignore
    }
  }

  return {
    messages,
    isLoading,
    streamingText,
    sessions,
    currentSessionId,
    addUserMessage,
    addBotMessage,
    setStreamingText,
    finalizeStream,
    sendMessage,
    fetchHistory,
    clearHistory,
    refreshSessions,
    createSession,
    switchSession,
    deleteSession,
    renameSession,
  }
})
