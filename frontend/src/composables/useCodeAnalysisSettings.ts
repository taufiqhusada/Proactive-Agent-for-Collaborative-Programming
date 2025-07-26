import { ref, watch } from 'vue'

// Frontend-only settings for code analysis
const codeAnalysisSettings = ref({
  enabled: true,
  delay: 2 // seconds
})

// Store settings in localStorage
const STORAGE_KEY = 'codeAnalysisSettings'

// Load settings from localStorage on startup
const loadSettings = () => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      codeAnalysisSettings.value = { ...codeAnalysisSettings.value, ...parsed }
    }
  } catch (error) {
    console.error('Failed to load code analysis settings:', error)
  }
}

// Save settings to localStorage whenever they change
const saveSettings = () => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(codeAnalysisSettings.value))
  } catch (error) {
    console.error('Failed to save code analysis settings:', error)
  }
}

// Watch for changes and auto-save
watch(codeAnalysisSettings, saveSettings, { deep: true })

// Load settings immediately
loadSettings()

export function useCodeAnalysisSettings() {
  const updateSettings = (newSettings: Partial<typeof codeAnalysisSettings.value>) => {
    codeAnalysisSettings.value = { ...codeAnalysisSettings.value, ...newSettings }
  }

  return {
    codeAnalysisSettings,
    updateSettings
  }
}
