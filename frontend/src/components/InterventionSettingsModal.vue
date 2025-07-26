<template>
    <div v-if="isVisible" class="modal-popup">
        <div class="modal-header">
            <h3>⚙️ AI Intervention Settings</h3>
            <button @click="closeModal" class="close-button">×</button>
        </div>
        
        <div class="modal-body">
            <p class="modal-description">
                Configure when Bob should automatically jump in to help during your pair programming session.
            </p>
                
                <div class="setting-item">
                    <div class="setting-info">
                        <div class="setting-title">
                            <span class="setting-icon">⏱️</span>
                            Idle Intervention
                        </div>
                        <div class="setting-description">
                            Bob will offer help (when necessary) after a period of silence in the conversation and coding
                        </div>
                        <div class="setting-controls">
                            <label class="time-input-label">
                                Delay: 
                                <input 
                                    type="number" 
                                    v-model.number="localSettings.idle_intervention_delay"
                                    :disabled="loading || !localSettings.idle_intervention_enabled"
                                    min="1"
                                    value="5"
                                    max="60"
                                    class="time-input"
                                > seconds
                            </label>
                        </div>
                    </div>
                    <label class="toggle-switch">
                        <input 
                            type="checkbox" 
                            v-model="localSettings.idle_intervention_enabled"
                            :disabled="loading"
                        >
                        <span class="slider"></span>
                    </label>
                </div>
                
                <div class="setting-item">
                    <div class="setting-info">
                        <div class="setting-title">
                            <span class="setting-icon">📊</span>
                            Progress Check
                        </div>
                        <div class="setting-description">
                            Bob will check on your progress periodically
                        </div>
                        <div class="setting-controls">
                            <label class="time-input-label">
                                Interval: 
                                <input 
                                    type="number" 
                                    v-model.number="localSettings.progress_check_interval"
                                    :disabled="loading || !localSettings.progress_check_enabled"
                                    min="10"
                                    value="30"
                                    max="300"
                                    class="time-input"
                                > seconds
                            </label>
                        </div>
                    </div>
                    <label class="toggle-switch">
                        <input 
                            type="checkbox" 
                            v-model="localSettings.progress_check_enabled"
                            :disabled="loading"
                        >
                        <span class="slider"></span>
                    </label>
                </div>
                
                <div class="setting-item">
                    <div class="setting-info">
                        <div class="setting-title">
                            <span class="setting-icon">🔍</span>
                            Code Analysis
                        </div>
                        <div class="setting-description">
                            Automatically analyze code blocks after you stop typing
                        </div>
                        <div class="setting-controls">
                            <label class="time-input-label">
                                Delay: 
                                <input 
                                    type="number" 
                                    v-model.number="localCodeAnalysisSettings.delay"
                                    :disabled="loading || !localCodeAnalysisSettings.enabled"
                                    min="0.5"
                                    step="0.5"
                                    value="3"
                                    max="100"
                                    class="time-input"
                                > seconds
                            </label>
                        </div>
                    </div>
                    <label class="toggle-switch">
                        <input 
                            type="checkbox" 
                            v-model="localCodeAnalysisSettings.enabled"
                            :disabled="loading"
                        >
                        <span class="slider"></span>
                    </label>
                </div>
            </div>
            
            <div class="modal-footer">
                <button @click="closeModal" class="cancel-button" :disabled="loading">
                    Cancel
                </button>
                <button @click="saveSettings" class="save-button" :disabled="loading || !hasChanges">
                    <span v-if="loading">Saving...</span>
                    <span v-else>Save Settings</span>
                </button>
            </div>
    </div>
</template>

<script>
import { defineComponent, ref, computed, watch } from 'vue'
import { useCodeAnalysisSettings } from '../composables/useCodeAnalysisSettings'

export default defineComponent({
    name: 'InterventionSettingsModal',
    props: {
        isVisible: {
            type: Boolean,
            default: false
        },
        settings: {
            type: Object,
            default: () => ({
                idle_intervention_enabled: true,
                idle_intervention_delay: 5,
                progress_check_enabled: true,
                progress_check_interval: 45
            })
        }
    },
    emits: ['close', 'save'],
    setup(props, { emit }) {
        const { codeAnalysisSettings, updateSettings } = useCodeAnalysisSettings()
        const loading = ref(false)
        const localSettings = ref({
            idle_intervention_enabled: true,
            idle_intervention_delay: 5,
            progress_check_enabled: true,
            progress_check_interval: 45
        })
        
        // Separate local settings for code analysis (frontend-only)
        const localCodeAnalysisSettings = ref({
            enabled: true,
            delay: 2
        })
        
        // Update local settings when props change
        watch(() => props.settings, (newSettings) => {
            if (newSettings) {
                localSettings.value = { ...newSettings }
            }
        }, { immediate: true })
        
        // Update local code analysis settings when global settings change
        watch(() => codeAnalysisSettings.value, (newSettings) => {
            localCodeAnalysisSettings.value = { ...newSettings }
        }, { immediate: true })
        
        const hasChanges = computed(() => {
            const backendChanges = JSON.stringify(localSettings.value) !== JSON.stringify(props.settings)
            const frontendChanges = JSON.stringify(localCodeAnalysisSettings.value) !== JSON.stringify(codeAnalysisSettings.value)
            return backendChanges || frontendChanges
        })
        
        const closeModal = () => {
            // Reset to original settings
            localSettings.value = { ...props.settings }
            localCodeAnalysisSettings.value = { ...codeAnalysisSettings.value }
            emit('close')
        }
        
        const saveSettings = async () => {
            loading.value = true
            try {
                await new Promise(resolve => setTimeout(resolve, 100)) // Small delay for UX
                
                // Save backend settings (only AI intervention settings)
                emit('save', { ...localSettings.value })
                
                // Save frontend settings (code analysis) locally
                updateSettings(localCodeAnalysisSettings.value)
                
            } finally {
                loading.value = false
            }
        }
        
        return {
            loading,
            localSettings,
            localCodeAnalysisSettings,
            hasChanges,
            closeModal,
            saveSettings
        }
    }
})
</script>

<style scoped>
/* Animation removed to prevent blur */

.modal-popup {
    position: fixed;
    top: 20px;
    right: 20px;
    background: #ffffff;
    border-radius: 8px;
    width: 450px;
    max-width: 90vw;
    max-height: 80vh;
    overflow: hidden;
    /* border: 3px solid #333; */
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    z-index: 1000;
    opacity: 1;
    /* color: #000; */
}

.modal-header {
    padding: 1.5rem;
    border-bottom: 1px solid #e2e8f0;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.modal-header h3 {
    margin: 0;
    font-size: 1.125rem;
    font-weight: 600;
    /* color: #000000; */
    opacity: 1;
}

.close-button {
    background: none;
    border: none;
    font-size: 1.5rem;
    color: #64748b;
    cursor: pointer;
    padding: 0;
    width: 2rem;
    height: 2rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    transition: all 0.2s;
}

.close-button:hover {
    background: #f1f5f9;
    color: #334155;
}

.modal-body {
    padding: 1.5rem;
    max-height: 60vh;
    overflow-y: auto;
}

.modal-description {
    /* color: #000000; */
    font-size: 0.875rem;
    margin: 0 0 1.5rem 0;
    line-height: 1.5;
    opacity: 1;
    font-weight: 500;
}

.setting-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem;
    border: 1px solid #ccc;
    border-radius: 4px;
    margin-bottom: 1rem;
}

.setting-item:hover {
    border-color: #999;
    background: #f9f9f9;
}

.setting-info {
    flex: 1;
    margin-right: 1rem;
}

.setting-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 700;
    color: #000000;
    margin-bottom: 0.25rem;
    opacity: 1;
}

.setting-icon {
    font-size: 1rem;
}

.setting-description {
    font-size: 0.875rem;
    color: #000000;
    line-height: 1.4;
    margin-bottom: 0.75rem;
    opacity: 1;
    font-weight: 400;
}

.setting-controls {
    margin-top: 0.5rem;
}

.time-input-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    color: #000000;
    font-weight: 500;
    opacity: 1;
}

.time-input {
    width: 60px;
    padding: 0.25rem 0.5rem;
    border: 1px solid #ccc;
    border-radius: 4px;
    font-size: 0.875rem;
    text-align: center;
    background: #fff;
    color: #000;
    opacity: 1;
}

.time-input:disabled {
    background: #f5f5f5;
    color: #999;
    cursor: not-allowed;
}

.time-input:focus {
    outline: none;
    border-color: #10b981;
    box-shadow: 0 0 0 1px #10b981;
}

.toggle-switch {
    position: relative;
    display: inline-block;
    width: 48px;
    height: 24px;
    cursor: pointer;
}

.toggle-switch input {
    opacity: 1;
    width: 0;
    height: 0;
}

.slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: #ccc;
    border-radius: 24px;
}

.slider:before {
    position: absolute;
    content: "";
    height: 18px;
    width: 18px;
    left: 3px;
    bottom: 3px;
    background-color: white;
    border-radius: 50%;
}

input:checked + .slider {
    background-color: #10b981;
}

input:checked + .slider:before {
    transform: translateX(24px);
}

input:disabled + .slider {
    opacity: 0.5;
    cursor: not-allowed;
}

.modal-footer {
    padding: 1.5rem;
    border-top: 1px solid #e2e8f0;
    display: flex;
    gap: 0.75rem;
    justify-content: flex-end;
}

.cancel-button, .save-button {
    padding: 0.5rem 1rem;
    border-radius: 6px;
    font-weight: 500;
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s;
    border: none;
}

.cancel-button {
    background: #f1f5f9;
    color: #000000;
    opacity: 1;
}

.cancel-button:hover:not(:disabled) {
    background: #e2e8f0;
}

.save-button {
    background: linear-gradient(135deg, #10b981, #059669);
    color: white;
}

.save-button:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(16, 185, 129, 0.3);
}

.save-button:disabled {
    opacity: 1;
    cursor: not-allowed;
    transform: none;
}

.cancel-button:disabled {
    opacity: 1;
    cursor: not-allowed;
}
</style>
