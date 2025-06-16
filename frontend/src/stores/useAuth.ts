import { defineStore } from 'pinia'
import axios from 'axios'

interface AuthState {
  token: string | null
  user: string | null
}

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL })

export const useAuth = defineStore('auth', {
  state: (): AuthState => ({ token: null, user: null }),

  actions: {
    async login(username: string, password: string) {
      const { data } = await api.post<{ access_token: string }>('/api/login', {
        username,
        password
      })
      this.token = data.access_token
      this.user = username
      localStorage.setItem('token', this.token)
    },

    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem('token')
    }
  }
})
