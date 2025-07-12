<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h2 class="login-title">
          🤝 Code and Learn 
          <span class="highlight-together">Together</span>
        </h2>
        <p class="login-subtitle">Join a coding session with your teammate</p>
        <p class="powered-by">Powered by human-human-AI</p>
      </div>
      
      <form @submit.prevent="submit" class="login-form">
        <div class="form-group">
          <label for="username" class="form-label">Your Name</label>
          <input 
            id="username"
            v-model="username" 
            placeholder="Enter your name"
            class="form-input"
            required
          />
        </div>
        
        <div class="form-group">
          <label for="roomId" class="form-label">Room Number</label>
          <input 
            id="roomId"
            v-model="roomId" 
            placeholder="Enter room number (e.g. room123)"
            class="form-input"
            required
          />
        </div>
        
        <div class="form-group">
          <label for="password" class="form-label">Password</label>
          <input 
            id="password"
            v-model="password" 
            type="password" 
            placeholder="Enter password"
            class="form-input"
            required
          />
        </div>
        
        <button type="submit" class="login-button" :disabled="!canSubmit">
          Join Room
        </button>
        
        <div v-if="error" class="error-message">
          {{ error }}
        </div>
      </form>
      
      <div class="login-hint">
        <p><strong>Hint:</strong> Password is "password"</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '@/stores/useAuth'
import { useSocket } from '@/lib/socket'

const username = ref('')
const password = ref('')
const roomId = ref('')
const error = ref('')

const auth = useAuth()
const { connect } = useSocket()
const router = useRouter()

const canSubmit = computed(() => {
  return username.value.trim() && password.value && roomId.value.trim()
})

async function submit() {
  error.value = ''
  
  // Validate password
  if (password.value !== 'password') {
    error.value = 'Invalid password. Hint: check the password hint below.'
    return
  }
  
  if (!username.value.trim()) {
    error.value = 'Please enter your name.'
    return
  }
  
  if (!roomId.value.trim()) {
    error.value = 'Please enter a room number.'
    return
  }
  
  try {
    // Login with the provided credentials
    await auth.login(username.value.trim(), password.value)
    
    // Connect to socket
    connect()
    
    // Navigate to the specified room
    router.push({ name: 'pair-room', params: { roomId: roomId.value.trim() } })
  } catch (err) {
    error.value = 'Login failed. Please try again.'
    console.error('Login error:', err)
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.login-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  padding: 2.5rem;
  width: 100%;
  max-width: 420px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.login-header {
  text-align: center;
  margin-bottom: 2rem;
}

.login-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: #2d3748;
  margin: 0 0 0.5rem 0;
}

.highlight-together {
  color: #667eea;
  font-weight: 600;
}

.login-subtitle {
  color: #718096;
  font-size: 0.95rem;
  margin: 0 0 0.25rem 0;
}

.powered-by {
  color: #4a5568;
  font-size: 0.75rem;
  margin: 0;
  font-style: italic;
  letter-spacing: 0.5px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-label {
  font-weight: 600;
  color: #4a5568;
  font-size: 0.875rem;
}

.form-input {
  padding: 0.875rem 1rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.95rem;
  transition: all 0.2s ease;
  background: white;
}

.form-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-input:required:invalid {
  border-color: #fed7d7;
}

.login-button {
  padding: 0.875rem 1.5rem;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-top: 0.5rem;
}

.login-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 10px 25px rgba(102, 126, 234, 0.3);
}

.login-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.error-message {
  background: #fed7d7;
  color: #c53030;
  padding: 0.75rem;
  border-radius: 6px;
  font-size: 0.875rem;
  border: 1px solid #feb2b2;
}

.login-hint {
  margin-top: 1.5rem;
  padding: 1rem;
  background: #f7fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  text-align: center;
}

.login-hint p {
  margin: 0;
  color: #4a5568;
  font-size: 0.875rem;
}

.login-hint strong {
  color: #2d3748;
}

/* Responsive design */
@media (max-width: 480px) {
  .login-card {
    padding: 1.5rem;
    margin: 1rem;
  }
  
  .login-title {
    font-size: 1.5rem;
  }
}
</style>
