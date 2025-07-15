import { ref } from 'vue'

export function useReflectionSession(socket: any, roomId: any) {
  // Simple reflection state (no highlighting)
  const showReflectionSession = ref(false)
  const reflectionSessionId = ref('')

  const startReflectionSession = () => {
    console.log('🎓 Starting reflection session for room:', roomId)
    
    // Use socket-based toggle instead of direct message
    socket.emit('toggle_reflection', {
      room: roomId,
      action: 'start'
    })
    
    // Update local state immediately for UI responsiveness
    const sessionId = 'reflection_' + Date.now()
    reflectionSessionId.value = sessionId
    showReflectionSession.value = true
    
    console.log('🎓 Set reflection session ID:', sessionId)
  }
  
  const stopReflectionSession = () => {
    console.log('🎓 Stopping reflection session for room:', roomId)
    
    // Add confirmation dialog to prevent accidental exits
    if (confirm('Are you sure you want to exit reflection mode? You can always start a new reflection session later.')) {
      // Use socket-based toggle to stop reflection
      socket.emit('toggle_reflection', {
        room: roomId,
        action: 'stop'
      })
      
      // Update local state immediately
      showReflectionSession.value = false
      reflectionSessionId.value = ''
      
      console.log('🎓 Reflection session stopped locally')
    }
  }
  
  const endReflectionSession = () => {
    console.log('🎓 Ending simple reflection session (legacy method)')
    showReflectionSession.value = false
    reflectionSessionId.value = ''
    
    // Send end reflection to backend (optional - for logging)
    socket.emit('end_reflection', { room: roomId })
    
    // Send a simple end message
    socket.emit('chat_message', {
      content: '🎓 Reflection session ended',
      username: 'System',
      userId: 'system',
      room: roomId,
      isAI: false,
      isSystem: true,
      timestamp: new Date().toISOString()
    })
  }

  // Handle session state changes for synchronization across users
  const handleSessionStateChange = (data: any) => {
    console.log('🔄 Reflection: Handling session state change:', data)
    
    if (data.action === 'reflection_started') {
      // Another user started reflection - update local state
      if (!showReflectionSession.value) {
        showReflectionSession.value = true
        reflectionSessionId.value = data.session_id || 'reflection_' + Date.now()
        console.log('📡 Reflection started by another user - updating local state')
      }
    } else if (data.action === 'reflection_stopped') {
      // Another user stopped reflection - update local state
      if (showReflectionSession.value) {
        showReflectionSession.value = false
        reflectionSessionId.value = ''
        console.log('📡 Reflection stopped by another user - updating local state')
      }
    } else if (data.action === 'session_reset') {
      // Session was reset - end any active reflection
      if (showReflectionSession.value) {
        showReflectionSession.value = false
        reflectionSessionId.value = ''
        console.log('📡 Session reset - ending reflection session')
      }
    }
    
    // Other session actions (session_started, session_reset) are handled by PairChat
    // but we can add notifications here if needed
    if (data.message && (data.action === 'reflection_started' || data.action === 'reflection_stopped')) {
      console.log('ℹ️ Session state notification:', data.message)
      // Could add a toast notification here if desired
    }
  }
  
  // Handle reflection session events from PairChat
  const handleReflectionSessionStarted = (sessionId: any) => {
    console.log('🎓 Reflection session started event from PairChat:', sessionId)
    showReflectionSession.value = true
    reflectionSessionId.value = sessionId
  }
  
  const handleReflectionSessionEnded = () => {
    console.log('🎓 Reflection session ended event from PairChat')
    showReflectionSession.value = false
    reflectionSessionId.value = ''
  }

  return {
    // State
    showReflectionSession,
    reflectionSessionId,
    
    // Methods
    startReflectionSession,
    stopReflectionSession,
    endReflectionSession,
    handleSessionStateChange,
    handleReflectionSessionStarted,
    handleReflectionSessionEnded
  }
}
