<template>
  <div class="chat-container" :class="{ 'individual-layout': currentMode === 'individual' }">
    <!-- AI Status Section (only in shared mode) -->
    <div v-if="currentMode === 'shared'" class="ai-status-section">
      <AIAgentStatus 
        :reflectionActive="showReflectionSession"
        @start-reflection="startReflectionSession"
        @stop-reflection="stopReflectionSession"
      />
    </div>
    
    <!-- Single PairChat instance for both modes -->
    <div :class="currentMode === 'shared' ? 'shared-mode' : 'team-chat-section'">
      <PairChat 
        ref="pairChat"
        :socket="socket" 
        :room-id="roomId" 
        :current-user-id="currentUserId"
        :username="username"
        :individual-mode="currentMode === 'individual'"
        :reflection-session-id="reflectionSessionId" 
        @reflection-session-started="handleReflectionSessionStarted"
        @reflection-session-ended="handleReflectionSessionEnded"
        @session-state-changed="handleSessionStateChanged"
        @clear-individual-ai-chat="clearIndividualAIChat"
      />
    </div>
    
    <!-- Individual AI Chat (only in individual mode) -->
    <div v-if="currentMode === 'individual'" class="ai-chat-section">
      <IndividualAIChat 
        ref="individualAIChat"
        :room-id="roomId"
        :user-id="currentUserId"
      />
    </div>
  </div>
</template>

<script>
import { defineComponent, ref, computed } from 'vue'
import PairChat from './PairChat.vue'
import IndividualAIChat from './IndividualAIChat.vue'
import AIAgentStatus from './AIAgentStatus.vue'
import { AIMode } from '@/services/aiModeService'

export default defineComponent({
  name: 'ChatContainer',
  components: {
    PairChat,
    IndividualAIChat,
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
    const teamChat = ref(null)
    const individualAIChat = ref(null)

    const isConnected = computed(() => {
      return props.socket && props.socket.connected
    })

    const handleModeChanged = (data) => {
      currentMode.value = data.mode
      
      // No need to notify backend - just switch frontend mode
      // Backend will be agnostic, we'll call different endpoints
      
      // Clear individual AI chat when switching to shared mode
      if (data.mode === AIMode.SHARED && individualAIChat.value) {
        individualAIChat.value.clearChat()
      }
    }

    // Forward events to parent
    const handleReflectionSessionStarted = (data) => {
      emit('reflection-session-started', data)
    }

    const handleReflectionSessionEnded = (data) => {
      emit('reflection-session-ended', data)
    }

    const handleSessionStateChanged = (data) => {
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
      if (currentMode.value === AIMode.SHARED) {
        if (pairChat.value) {
          pairChat.value.addMessage(message)
        }
      } else {
        // In individual mode, add to team chat
        if (teamChat.value) {
          teamChat.value.addMessage(message)
        }
      }
    }

    // Method to clear individual AI chat (called during session reset)
    const clearIndividualAIChat = () => {
      if (individualAIChat.value) {
        individualAIChat.value.clearChat()
        console.log('🧹 Cleared individual AI chat during session reset')
      }
    }

    return {
      currentMode,
      pairChat,
      teamChat,
      individualAIChat,
      isConnected,
      handleModeChanged,
      handleReflectionSessionStarted,
      handleReflectionSessionEnded,
      handleSessionStateChanged,
      startReflectionSession,
      stopReflectionSession,
      addMessage,
      clearIndividualAIChat
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

.shared-mode {
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

.team-chat-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0; /* Critical: allows shrinking below content size */
  overflow: hidden; /* Prevent container overflow */
}

.ai-chat-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0; /* Critical: allows shrinking below content size */
  overflow: hidden; /* Prevent container overflow */
}

.section-header {
  margin-bottom: 0.5rem;
}

.section-title {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: #2d3748;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.section-icon {
  font-size: 1rem;
}

/* Individual mode layout - split screen */
.individual-layout {
  height: 100vh; /* Full viewport height */
  max-height: 100vh; /* Don't exceed viewport */
}

.individual-layout .team-chat-section {
  /* Team chat takes up half the available space in individual mode */
  flex: 0 1 50%;
  min-height: 300px; /* Minimum readable height */
  max-height: 50vh; /* Don't exceed half viewport */
}

.individual-layout .ai-chat-section {
  /* AI chat takes up the other half in individual mode */
  flex: 0 1 50%;
  min-height: 300px; /* Minimum readable height */
  max-height: 50vh; /* Don't exceed half viewport */
}
</style>
