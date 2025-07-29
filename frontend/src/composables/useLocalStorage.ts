import { ref, watch, type Ref } from 'vue'

/**
 * Composable for persisting reactive data in localStorage
 */
export function useLocalStorage<T>(key: string, defaultValue: T): [Ref<T>, (value: T) => void] {
  // Try to get the value from localStorage
  const storedValue = localStorage.getItem(key)
  
  let initialValue: T
  try {
    initialValue = storedValue ? JSON.parse(storedValue) : defaultValue
  } catch (error) {
    console.warn(`Failed to parse localStorage value for key "${key}":`, error)
    initialValue = defaultValue
  }
  
  const value = ref<T>(initialValue) as Ref<T>
  
  // Save to localStorage whenever the value changes
  const setValue = (newValue: T) => {
    try {
      value.value = newValue
      localStorage.setItem(key, JSON.stringify(newValue))
    } catch (error) {
      console.error(`Failed to save to localStorage for key "${key}":`, error)
    }
  }
  
  // Watch for changes and save to localStorage
  watch(value, (newValue) => {
    try {
      localStorage.setItem(key, JSON.stringify(newValue))
    } catch (error) {
      console.error(`Failed to save to localStorage for key "${key}":`, error)
    }
  }, { deep: true })
  
  return [value, setValue]
}

/**
 * Composable specifically for persisting room state
 */
export function useRoomPersistence(roomId: string) {
  const STORAGE_KEY = `room_${roomId}_state`
  const EXPIRY_HOURS = 24 // Keep room state for 24 hours
  
  interface RoomState {
    code: string
    language: string
    timestamp: number
  }
  
  const defaultState: RoomState = {
    code: 'print("Hello")',
    language: 'python',
    timestamp: Date.now()
  }
  
  const [roomState, setRoomState] = useLocalStorage<RoomState>(STORAGE_KEY, defaultState)
  
  // Check if stored state is still valid (not expired)
  const isStateValid = () => {
    const now = Date.now()
    const stateAge = now - roomState.value.timestamp
    const expiryTime = EXPIRY_HOURS * 60 * 60 * 1000 // Convert hours to milliseconds
    
    return stateAge < expiryTime
  }
  
  // Get persisted code, or return default if expired
  const getPersistedCode = (): string => {
    if (isStateValid()) {
      console.log(`📁 Retrieved persisted code for room ${roomId}:`, roomState.value.code.substring(0, 50) + '...')
      return roomState.value.code
    } else {
      console.log(`📁 Persisted code for room ${roomId} has expired, using default`)
      return defaultState.code
    }
  }
  
  // Get persisted language, or return default if expired
  const getPersistedLanguage = (): string => {
    if (isStateValid()) {
      console.log(`📁 Retrieved persisted language for room ${roomId}:`, roomState.value.language)
      return roomState.value.language
    } else {
      console.log(`📁 Persisted language for room ${roomId} has expired, using default`)
      return defaultState.language
    }
  }
  
  // Save current room state
  const saveRoomState = (code: string, language: string) => {
    const newState: RoomState = {
      code,
      language,
      timestamp: Date.now()
    }
    setRoomState(newState)
    console.log(`📁 Saved room state for room ${roomId}`)
  }
  
  // Clear persisted state (useful for cleanup)
  const clearPersistedState = () => {
    localStorage.removeItem(STORAGE_KEY)
    console.log(`📁 Cleared persisted state for room ${roomId}`)
  }
  
  // Cleanup old room states (optional - call this on app startup)
  const cleanupExpiredStates = () => {
    const keys = Object.keys(localStorage)
    const roomKeys = keys.filter(key => key.startsWith('room_') && key.endsWith('_state'))
    
    let cleanedCount = 0
    roomKeys.forEach(key => {
      try {
        const data = JSON.parse(localStorage.getItem(key) || '{}')
        if (data.timestamp) {
          const now = Date.now()
          const age = now - data.timestamp
          const expiryTime = EXPIRY_HOURS * 60 * 60 * 1000
          
          if (age > expiryTime) {
            localStorage.removeItem(key)
            cleanedCount++
          }
        }
      } catch (error) {
        // Remove corrupted entries
        localStorage.removeItem(key)
        cleanedCount++
      }
    })
    
    if (cleanedCount > 0) {
      console.log(`📁 Cleaned up ${cleanedCount} expired room states`)
    }
  }
  
  return {
    getPersistedCode,
    getPersistedLanguage,
    saveRoomState,
    clearPersistedState,
    isStateValid,
    cleanupExpiredStates
  }
}
