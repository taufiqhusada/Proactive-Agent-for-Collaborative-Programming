import { io, Socket } from 'socket.io-client'
import { useAuth } from '@/stores/useAuth'

let socket: Socket

export function useSocket() {
  const auth = useAuth()

  if (!socket) {
    socket = io(import.meta.env.VITE_WS_URL + '/ws', {
      autoConnect: false,
      transports: ['websocket', 'polling'],
      timeout: 20000,
      forceNew: true
    })

    socket.on('connect_error', (error) => {
      console.error('Socket connection error:', error)
    })

    socket.on('disconnect', (reason) => {
      console.log('Socket disconnected:', reason)
    })
  }

  function connect() {
    socket.auth = { token: auth.token }
    if (!socket.connected) {
      console.log('Attempting to connect to:', import.meta.env.VITE_WS_URL + '/ws')
      socket.connect()
    }
  }

  return { socket, connect }
}
