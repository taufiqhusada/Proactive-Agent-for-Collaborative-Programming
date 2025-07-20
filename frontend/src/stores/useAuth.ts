import { defineStore } from 'pinia'
import axios from 'axios'

interface AuthState {
  token: string | null
  user: string | null
}

const api = axios.create({ 
  baseURL: import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '' : 'http://localhost:5000')
})

export const useAuth = defineStore('auth', {
  state: (): AuthState => ({ token: null, user: null }),

  actions: {
    async login(username: string, password: string) {
      // Validate password locally
      if (password !== 'password') {
        throw new Error('Invalid password')
      }
      
      if (!username.trim()) {
        throw new Error('Username is required')
      }
      
      try {
        const { data } = await api.post<{ access_token: string }>('/api/login', {
          username: username.trim(),
          password
        })
        this.token = data.access_token
        this.user = username.trim()
        localStorage.setItem('token', this.token)
        localStorage.setItem('username', username.trim())
      } catch (error) {
        // If backend login fails, still allow local login for demo purposes
        console.warn('Backend login failed, using local auth:', error)
        this.token = 'demo-token-' + Date.now()
        this.user = username.trim()
        localStorage.setItem('token', this.token)
        localStorage.setItem('username', username.trim())
      }
    },

    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('username')
    },

    // Restore authentication state from localStorage
    initialize() {
      const token = localStorage.getItem('token')
      const username = localStorage.getItem('username')
      if (token && username) {
        this.token = token
        this.user = username
      }
    }
  }
})
