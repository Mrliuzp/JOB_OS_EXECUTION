import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const workerStatus = ref('等待连接')
  let socket: WebSocket | null = null

  function connectWorkerStatus(): void {
    if (socket) return
    const url = import.meta.env.VITE_WS_URL ?? 'ws://127.0.0.1:8000/api/v1/ws/worker-status'
    socket = new WebSocket(url)
    socket.onmessage = (event: MessageEvent<string>) => {
      const payload = JSON.parse(event.data) as { status?: string }
      workerStatus.value = payload.status ?? '未知'
    }
    socket.onclose = () => {
      workerStatus.value = '已断开'
      socket = null
    }
    socket.onerror = () => {
      workerStatus.value = '连接失败'
    }
  }

  return { workerStatus, connectWorkerStatus }
})
