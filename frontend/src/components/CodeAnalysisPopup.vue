<template>
  <teleport to="body">
    <div 
      v-if="visible" 
      ref="popupRef"
      class="code-analysis-popup"
      :style="{ 
        left: position.x + 'px', 
        top: position.y + 'px',
        zIndex: 9999
      }"
      @click.stop
    >
      <div class="popup-content">
        <button 
          class="popup-button analyze-button"
          @click="handleAnalyzeClick"
          :disabled="analyzing"
        >
          <span class="button-icon">🔍</span>
          <span class="button-text">
            {{ analyzing ? 'Analyzing...' : 'Analyze Code Block' }}
          </span>
        </button>
        
        <div class="popup-divider"></div>
        
        <button 
          class="popup-button cancel-button"
          @click="handleCancel"
        >
          <span class="button-icon">✕</span>
          <span class="button-text">Cancel</span>
        </button>
      </div>
    </div>
  </teleport>
</template>

<script>
import { ref, nextTick, onMounted, onUnmounted, watch } from 'vue'

export default {
  name: 'CodeAnalysisPopup',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    position: {
      type: Object,
      default: () => ({ x: 0, y: 0 })
    },
    codeBlock: {
      type: Object,
      default: null
    }
  },
  emits: ['analyze', 'close'],
  setup(props, { emit }) {
    const popupRef = ref(null)
    const analyzing = ref(false)

    const handleAnalyzeClick = () => {
      if (props.codeBlock) {
        analyzing.value = true
        emit('analyze', props.codeBlock)
        
        // Reset analyzing state after a delay
        setTimeout(() => {
          analyzing.value = false
          emit('close')
        }, 1000)
      }
    }

    const handleCancel = () => {
      emit('close')
    }

    const handleClickOutside = (event) => {
      if (popupRef.value && !popupRef.value.contains(event.target)) {
        emit('close')
      }
    }

    const handleEscKey = (event) => {
      if (event.key === 'Escape') {
        emit('close')
      }
    }

    const adjustPosition = () => {
      if (!popupRef.value) return

      nextTick(() => {
        const popup = popupRef.value
        const rect = popup.getBoundingClientRect()
        const viewportWidth = window.innerWidth
        const viewportHeight = window.innerHeight

        let newX = props.position.x
        let newY = props.position.y

        // Adjust horizontal position if popup goes off screen
        if (newX + rect.width > viewportWidth) {
          newX = viewportWidth - rect.width - 10
        }
        if (newX < 10) {
          newX = 10
        }

        // Adjust vertical position if popup goes off screen
        if (newY + rect.height > viewportHeight) {
          newY = props.position.y - rect.height - 5 // Position above cursor
        }
        if (newY < 10) {
          newY = 10
        }

        // Apply adjusted position
        popup.style.left = newX + 'px'
        popup.style.top = newY + 'px'
      })
    }

    onMounted(() => {
      document.addEventListener('click', handleClickOutside)
      document.addEventListener('keydown', handleEscKey)
      adjustPosition()
    })

    onUnmounted(() => {
      document.removeEventListener('click', handleClickOutside)
      document.removeEventListener('keydown', handleEscKey)
    })

    // Watch for position changes and adjust
    watch(() => props.visible, (newVisible) => {
      if (newVisible) {
        nextTick(adjustPosition)
      }
    })

    return {
      popupRef,
      analyzing,
      handleAnalyzeClick,
      handleCancel
    }
  }
}
</script>

<style scoped>
.code-analysis-popup {
  position: fixed;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 14px;
  min-width: 200px;
  animation: popupFadeIn 0.15s ease-out;
}

@keyframes popupFadeIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.popup-content {
  padding: 8px;
}

.popup-button {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 8px 12px;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.15s ease;
  text-align: left;
  color: #374151;
}

.popup-button:hover:not(:disabled) {
  background: #f3f4f6;
}

.popup-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.analyze-button:hover:not(:disabled) {
  background: #f0f9ff;
  color: #0369a1;
}

.cancel-button:hover {
  background: #fef2f2;
  color: #dc2626;
}

.button-icon {
  margin-right: 8px;
  font-size: 14px;
}

.button-text {
  flex: 1;
}

.popup-divider {
  height: 1px;
  background: #e5e7eb;
  margin: 4px 0;
}

/* Dark theme support */
@media (prefers-color-scheme: dark) {
  .code-analysis-popup {
    background: #1f2937;
    border-color: #374151;
    color: #f9fafb;
  }

  .popup-button {
    color: #f9fafb;
  }

  .popup-button:hover:not(:disabled) {
    background: #374151;
  }

  .analyze-button:hover:not(:disabled) {
    background: #1e3a8a;
    color: #93c5fd;
  }

  .cancel-button:hover {
    background: #7f1d1d;
    color: #fca5a5;
  }

  .popup-divider {
    background: #4b5563;
  }
}
</style>
