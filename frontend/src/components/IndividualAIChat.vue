<template>
  <div class="individual-ai-chat">
    <div class="chat-header">
      <h6 class="chat-title">
        <span class="chat-icon">👨‍💻</span>
        Personal AI Assistant
      </h6>
    </div>

    <div class="chat-messages" ref="messagesContainer">
      <div v-for="message in messages" :key="message.id" class="message-wrapper">
        <div 
          :class="[
            'message', 
            { 
              'user-message': !message.isAI,
              'ai-message': message.isAI
            }
          ]"
        >
          <div class="message-header">
            <span class="username">
              <span v-if="message.isAI" class="ai-badge">👨‍💻</span>
              {{ message.isAI ? 'AI Assistant' : 'You' }}
            </span>
            <span class="timestamp">{{ formatTime(message.timestamp) }}</span>
          </div>
          <div class="message-content">{{ message.content }}</div>
        </div>
      </div>
      <div v-if="messages.length === 0" class="empty-chat">
        <div class="empty-content">
          <span class="empty-icon">💭</span>
          <span class="empty-text">Ask your personal AI assistant anything!</span>
          <span class="empty-subtext">This conversation is private to you</span>
        </div>
      </div>
      <div v-if="isTyping" class="typing-indicator">
        <div class="typing-content">
          <span class="ai-badge">👨‍💻</span>
          <span class="typing-text">AI is thinking...</span>
          <div class="typing-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    </div>

    <div class="chat-input">
      <div class="input-wrapper">
        <input 
          v-model="newMessage" 
          @keyup.enter="sendMessage"
          placeholder="Ask your personal AI assistant..."
          class="message-input"
          :disabled="isTyping"
        />
        <button 
          @click="sendMessage"
          :disabled="!newMessage.trim() || isTyping"
          class="send-button"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22,2 15,22 11,13 2,9"></polygon>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { defineComponent, ref, nextTick, onMounted, onUnmounted } from 'vue'

export default defineComponent({
  name: 'IndividualAIChat',
  props: {
    roomId: {
      type: String,
      required: true
    },
    userId: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const messages = ref([])
    const newMessage = ref('')
    const isTyping = ref(false)
    const messagesContainer = ref(null)
    const messageIdCounter = ref(0)

    const scrollToBottom = () => {
      nextTick(() => {
        if (messagesContainer.value) {
          messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
        }
      })
    }

    const formatTime = (timestamp) => {
      return new Date(timestamp).toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit' 
      })
    }

    const addMessage = (content, isAI = false) => {
      const message = {
        id: `msg_${messageIdCounter.value++}`,
        content,
        isAI,
        timestamp: new Date().toISOString(),
        userId: isAI ? 'ai_assistant' : props.userId
      }
      
      messages.value.push(message)
      scrollToBottom()
      return message
    }

    const sendMessage = async () => {
      if (!newMessage.value.trim()) return

      const userMessage = addMessage(newMessage.value.trim(), false)
      newMessage.value = ''
      isTyping.value = true
      
      try {
        // Use REST API instead of socket
        const response = await fetch('/api/individual-ai', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            userId: props.userId,
            roomId: props.roomId,
            message: userMessage.content
          })
        })

        const data = await response.json()
        
        if (response.ok && data.response) {
          addMessage(data.response, true)
        } else {
          addMessage(data.error || 'Failed to get AI response', true)
        }
      } catch (error) {
        console.error('Error sending message to AI:', error)
        addMessage('Sorry, I encountered an error. Please try again.', true)
      } finally {
        isTyping.value = false
      }
    }

    const handleIndividualAIResponse = (data) => {
      // No longer needed - using REST API
    }

    const clearChat = () => {
      messages.value = []
      messageIdCounter.value = 0
    }

    // Handle AI messages redirected from shared chat in personal mode
    const handleRedirectedAIMessage = (event) => {
      console.log('🤖 IndividualAIChat: Received redirected AI message', event.detail)
      const { content, timestamp, hasAudio, isReflection, isExecutionHelp } = event.detail
      
      console.log('✅ IndividualAIChat: Adding AI message')
      
      // Add the AI message to personal chat
      const aiMessage = {
        id: `redirected_${messageIdCounter.value++}`,
        content,
        isAI: true,
        timestamp: timestamp || new Date().toISOString(),
        userId: 'ai_assistant',
        isReflection: isReflection || false,
        isExecutionHelp: isExecutionHelp || false
      }
      
      messages.value.push(aiMessage)
      scrollToBottom()
    }

    // Setup lifecycle hooks
    onMounted(() => {
      // Listen for AI messages redirected from shared chat in personal mode
      window.addEventListener('ai-message-for-personal-chat', handleRedirectedAIMessage)
    })

    onUnmounted(() => {
      // Clean up event listener
      window.removeEventListener('ai-message-for-personal-chat', handleRedirectedAIMessage)
    })

    // No socket event handlers needed for REST API approach

    return {
      messages,
      newMessage,
      isTyping,
      messagesContainer,
      sendMessage,
      formatTime,
      clearChat,
      addMessage
    }
  }
})
</script>

<style scoped>
.individual-ai-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.chat-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-title {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.chat-icon {
  font-size: 1rem;
}

.ai-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #e53e3e;
  transition: background-color 0.3s ease;
}

.status-indicator.online {
  background: #38a169;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  background: #f8fafc;
}

.message-wrapper {
  display: flex;
  flex-direction: column;
}

.message {
  max-width: 85%;
  padding: 0.75rem;
  border-radius: 12px;
  background: white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.user-message {
  align-self: flex-end;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.ai-message {
  align-self: flex-start;
  background: white;
  border: 1px solid #e2e8f0;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.25rem;
  gap: 0.5rem;
}

.username {
  font-weight: 600;
  font-size: 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.user-message .username {
  color: rgba(255, 255, 255, 0.9);
}

.ai-message .username {
  color: #4a5568;
}

.ai-badge {
  font-size: 0.75rem;
}

.timestamp {
  font-size: 0.625rem;
  opacity: 0.7;
}

.message-content {
  font-size: 0.875rem;
  line-height: 1.4;
  word-wrap: break-word;
}

.empty-chat {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-content {
  text-align: center;
  color: #718096;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.empty-icon {
  font-size: 2rem;
  opacity: 0.5;
}

.empty-text {
  font-size: 0.875rem;
  font-weight: 500;
}

.empty-subtext {
  font-size: 0.75rem;
  opacity: 0.7;
}

.typing-indicator {
  display: flex;
  align-items: center;
  padding: 0.5rem 0.75rem;
  background: white;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  max-width: 150px;
}

.typing-content {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: #718096;
}

.typing-dots {
  display: flex;
  gap: 0.25rem;
}

.typing-dots span {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #cbd5e0;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-dots span:nth-child(1) { animation-delay: -0.32s; }
.typing-dots span:nth-child(2) { animation-delay: -0.16s; }

@keyframes typing {
  0%, 80%, 100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.chat-input {
  padding: 1rem;
  background: white;
  border-top: 1px solid #e2e8f0;
}

.input-wrapper {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.message-input {
  flex: 1;
  padding: 0.75rem 1rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  font-size: 0.875rem;
  transition: all 0.2s ease;
}

.message-input:focus {
  outline: none;
  border-color: #667eea;
  background: white;
}

.send-button {
  padding: 0.75rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.send-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.send-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}
</style>
