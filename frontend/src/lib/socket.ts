import { io, Socket } from 'socket.io-client'
import { useAuth } from '@/stores/useAuth'

let socket: Socket

export function useSocket() {
  const auth = useAuth()

  if (!socket) {
    // In production, connect directly to backend for WebSocket support
    // In development, use localhost
    const wsUrl = import.meta.env.VITE_WS_URL || 
                  (import.meta.env.PROD 
                    ? 'https://hhaipp-00001-9xb-cfnm2zc7da-uk.a.run.app' 
                    : 'http://localhost:5000')
    
    console.log('Socket connecting to:', wsUrl)
    
    socket = io(wsUrl + '/ws', {
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
      console.log('Attempting to connect socket...')
      socket.connect()
    }
  }

  return { socket, connect }
}
