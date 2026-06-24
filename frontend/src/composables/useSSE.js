import { ref, onMounted, onUnmounted } from 'vue'

export function useSSE(url, onMessage, onError) {
  const isConnected = ref(false)
  let eventSource = null

  function connect() {
    const token = localStorage.getItem('hr_token')
    eventSource = new EventSource(`${url}?token=${token}`)

    eventSource.onopen = () => {
      isConnected.value = true
    }

    eventSource.onmessage = (event) => {
      onMessage(event.data)
    }

    eventSource.onerror = (err) => {
      isConnected.value = false
      if (onError) onError(err)
      eventSource.close()
    }
  }

  function disconnect() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
      isConnected.value = false
    }
  }

  onMounted(() => {
    connect()
  })

  onUnmounted(() => {
    disconnect()
  })

  return { isConnected, connect, disconnect }
}
