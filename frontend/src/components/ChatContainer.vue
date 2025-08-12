<template>
  <div class="chat-container">
    <!-- AI Status Section (show when AI is available - both shared and individual modes) -->
    <div v-if="currentMode !== 'none'" class="ai-status-section">
      <AIAgentStatus 
        :reflectionActive="showReflectionSession"
        :sessionStarted="sessionStarted"
        @start-reflection="startReflectionSession"
        @stop-reflection="stopReflectionSession"
      />
    </div>
    
    <!-- Single PairChat instance for all modes -->
    <div class="single-chat-section">
      <PairChat 
        ref="pairChat"
        :socket="socket" 
        :room-id="actualRoomId" 
        :current-user-id="currentUserId"
        :username="username"
        :individual-mode="currentMode === 'individual'"
        :no-ai-mode="currentMode === 'none'"
        :reflection-session-id="reflectionSessionId" 
        :current-problem="currentProblem"
        @reflection-session-started="handleReflectionSessionStarted"
        @reflection-session-ended="handleReflectionSessionEnded"
        @session-state-changed="handleSessionStateChanged"
      />
    </div>
  </div>
</template>

<script>
import { defineComponent, ref, computed } from 'vue'
import PairChat from './PairChat.vue'
import AIAgentStatus from './AIAgentStatus.vue'
import { AIMode } from '@/services/aiModeService'

export default defineComponent({
  name: 'ChatContainer',
  components: {
    PairChat,
    AIAgentStatus
  },
  props: {
    socket: {
      type: Object,
      required: true
    },
    roomId: {
      type: String,
      required: true
    },
    currentUserId: {
      type: String,
      required: true
    },
    username: {
      type: String,
      required: true
    },
    reflectionSessionId: {
      type: String,
      default: null
    },
    showReflectionSession: {
      type: Boolean,
      default: false
    },
    currentProblem: {
      type: Object,
      default: null
    }
  },
  emits: [
    'reflection-session-started',
    'reflection-session-ended',
    'start-reflection',
    'stop-reflection',
    'session-state-changed'
  ],
  setup(props, { emit }) {
    const currentMode = ref(AIMode.SHARED)
    const pairChat = ref(null)
    const sessionStarted = ref(false)
    
    const isConnected = computed(() => {
      return props.socket && props.socket.connected
    })

    // Generate actual room ID based on mode
    const actualRoomId = computed(() => {
      if (currentMode.value === 'individual') {
        // Create personal room: roomId_personal_userId
        return `${props.roomId}_personal_${props.currentUserId}`
      }
      // For shared and none modes, use original room ID
      return props.roomId
    })

    const handleModeChanged = (data) => {
      console.log('🔄 AI mode changed to:', data.mode)
      currentMode.value = data.mode
      
      // When switching modes, the actualRoomId will automatically change
      // The PairChat component will handle the room switching via the reactivity
    }

    // Forward events to parent
    const handleReflectionSessionStarted = (data) => {
      emit('reflection-session-started', data)
    }

    const handleReflectionSessionEnded = (data) => {
      emit('reflection-session-ended', data)
    }

    const handleSessionStateChanged = (data) => {
      // Track session state locally
      if (data.sessionStarted !== undefined) {
        sessionStarted.value = data.sessionStarted
        console.log('🔄 Session state changed in ChatContainer:', sessionStarted.value)
      }
      emit('session-state-changed', data)
    }

    const startReflectionSession = () => {
      emit('start-reflection')
    }

    const stopReflectionSession = () => {
      emit('stop-reflection')
    }

    // Expose method to add messages from parent (for code runner)
    const addMessage = (message) => {
      if (pairChat.value) {
        pairChat.value.addMessage(message)
      }
    }

    return {
      currentMode,
      pairChat,
      sessionStarted,
      isConnected,
      actualRoomId,
      handleModeChanged,
      handleReflectionSessionStarted,
      handleReflectionSessionEnded,
      handleSessionStateChanged,
      startReflectionSession,
      stopReflectionSession,
      addMessage
    }
  }
})
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 1rem;
  overflow: hidden; /* Prevent container from growing */
}

.single-chat-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-height: 0; /* Allow shrinking */
  overflow: hidden; /* Prevent growing */
}

.ai-status-section {
  flex-shrink: 0;
}
</style>
