<template>
  <div class="ai-mode-toggle-header">
    <div class="mode-dropdown">
      <select 
        v-model="currentMode" 
        @change="handleModeChange"
        :disabled="sessionStarted"
        :class="['mode-select', { 'disabled': sessionStarted }]"
      >
        <option value="shared">🤝 Shared AI</option>
        <option value="individual">👤 Personal AI</option>
      </select>
      <div class="dropdown-icon">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="6,9 12,15 18,9"></polyline>
        </svg>
      </div>
    </div>
    <div v-if="sessionStarted" class="session-lock-indicator" title="AI mode is locked during active session">
      🔒
    </div>
  </div>
</template>

<script>
import { defineComponent, ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { aiModeService, AIMode } from '@/services/aiModeService'

export default defineComponent({
  name: 'AIModeToggle',
  props: {
    roomId: {
      type: String,
      required: true
    },
    userId: {
      type: String,
      required: true
    },
    socket: {
      type: Object,
      required: true
    },
    sessionStarted: {
      type: Boolean,
      default: false
    }
  },
  emits: ['mode-changed'],
  setup(props, { emit }) {
    const currentMode = ref(AIMode.SHARED)
    
    // Use computed property to react to prop changes
    const sessionStarted = computed(() => props.sessionStarted)

    const handleModeChange = () => {
      if (sessionStarted.value) {
        console.warn('Cannot change AI mode during active session')
        // Revert to current mode
        currentMode.value = aiModeService.getCurrentMode()
        return
      }

      const newMode = currentMode.value
      aiModeService.setMode(newMode, props.roomId, props.userId, true) // broadcast = true
      
      emit('mode-changed', {
        mode: newMode,
        channelName: aiModeService.getAIChannelName(),
        changedBy: props.userId
      })
    }

    const handleAIModeChanged = (data) => {
      const { mode, changedBy } = data
      console.log(`AI mode changed to ${mode} by user ${changedBy}`)
      
      // Update local state without broadcasting (to avoid loops)
      aiModeService.setMode(mode, props.roomId, props.userId, false) // broadcast = false
      currentMode.value = mode
      
      emit('mode-changed', {
        mode: mode,
        channelName: aiModeService.getAIChannelName(),
        changedBy: changedBy
      })
    }

    onMounted(() => {
      // Initialize with current mode
      currentMode.value = aiModeService.getCurrentMode()
      aiModeService.setMode(currentMode.value, props.roomId, props.userId, false)
      aiModeService.setSocket(props.socket)
      
      // Listen for AI mode changes from other users
      props.socket.on('ai_mode_changed', handleAIModeChanged)
      
      // Set initial session state
      aiModeService.setSessionState(props.sessionStarted)
    })

    onUnmounted(() => {
      // Clean up socket listener
      props.socket.off('ai_mode_changed', handleAIModeChanged)
    })

    // Watch for session state changes from parent
    watch(() => props.sessionStarted, (newValue) => {
      aiModeService.setSessionState(newValue)
    })

    return {
      currentMode,
      sessionStarted,
      handleModeChange
    }
  }
})
</script>

<style scoped>
.ai-mode-toggle-header {
  display: flex;
  align-items: center;
}

.mode-dropdown {
  position: relative;
  display: inline-block;
}

.mode-select {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  padding: 0.4rem 2rem 0.4rem 0.75rem;
  font-size: 0.8rem;
  font-weight: 500;
  color: #2d3748;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 120px;
  outline: none;
}

.mode-select:hover {
  background: rgba(255, 255, 255, 0.95);
  border-color: rgba(0, 0, 0, 0.2);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.mode-select:focus {
  background: white;
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.mode-select.disabled {
  background: rgba(243, 244, 246, 0.9);
  color: #9ca3af;
  cursor: not-allowed;
  opacity: 0.6;
}

.mode-select.disabled:hover {
  background: rgba(243, 244, 246, 0.9);
  border-color: rgba(0, 0, 0, 0.1);
  box-shadow: none;
}

.session-lock-indicator {
  margin-left: 0.5rem;
  font-size: 0.8rem;
  opacity: 0.7;
}

.mode-select option {
  background: #2d3748;
  color: white;
  padding: 0.5rem;
  font-weight: 500;
}

.mode-select option:hover {
  background: #4a5568;
}

.dropdown-icon {
  position: absolute;
  right: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  color: #4a5568;
  transition: transform 0.2s ease;
}

.mode-dropdown:hover .dropdown-icon {
  color: #2d3748;
}

/* Focus state for dropdown icon */
.mode-select:focus + .dropdown-icon {
  transform: translateY(-50%) rotate(180deg);
}

/* Custom scrollbar for dropdown options (webkit) */
.mode-select::-webkit-scrollbar {
  width: 6px;
}

.mode-select::-webkit-scrollbar-track {
  background: #2d3748;
}

.mode-select::-webkit-scrollbar-thumb {
  background: #4a5568;
  border-radius: 3px;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .mode-select {
    font-size: 0.75rem;
    padding: 0.35rem 1.75rem 0.35rem 0.65rem;
    min-width: 110px;
  }
  
  .dropdown-icon {
    right: 0.65rem;
  }
}
</style>
