<template>
    <div class="ai-agent-status">
        <div class="ai-indicator">
            <div class="ai-avatar">
                <span class="ai-emoji">👨‍💻</span>
            </div>
            <div class="ai-info">
                <div class="ai-name">Bob</div>
                <div class="ai-status">
                    <span class="status-dot" :class="{ 'reflection-mode': reflectionActive }"></span>
                    {{ reflectionActive ? 'Reflection Mode Active' : 'AI Active' }}
                </div>
            </div>
            <!-- Action Buttons Container -->
            <div class="action-buttons">
                <!-- Intervention Settings Button -->
                <button 
                    @click="showInterventionSettings = true"
                    class="settings-button"
                    title="Configure AI intervention settings"
                >
                    ⚙️
                </button>
            </div>
        </div>
    </div>
    
    <!-- Intervention Settings Modal -->
    <InterventionSettingsModal 
        :isVisible="showInterventionSettings"
        :settings="interventionSettings"
        @close="showInterventionSettings = false"
        @save="handleSaveInterventionSettings"
    />
    
    <!-- Progress Check Notification Popup - rendered at body level to avoid clipping -->
    <Teleport to="body">
        <transition name="progress-notification">
            <div 
                v-if="showProgressNotification" 
                class="progress-notification-bubble"
                @click="dismissProgressNotification"
                ref="progressNotificationRef"
            >
                <div class="progress-content">
                    <div class="progress-icon">📊</div>
                    <div class="progress-text">{{ progressNotificationText }}</div>
                    <div class="progress-dismiss">×</div>
                </div>
            </div>
        </transition>
    </Teleport>
</template>

<script>
import { defineComponent, ref, onMounted, onUnmounted } from 'vue'
import InterventionSettingsModal from './InterventionSettingsModal.vue'

export default defineComponent({
    name: 'AIAgentStatus',
    components: {
        InterventionSettingsModal
    },
    props: {
        isActive: {
            type: Boolean,
            default: true
        },
        reflectionActive: {
            type: Boolean,
            default: false
        },
        showDescription: {
            type: Boolean,
            default: false
        },
        sessionStarted: {
            type: Boolean,
            default: false
        },
        socket: {
            type: Object,
            default: null
        },
        roomId: {
            type: String,
            default: ''
        }
    },
    emits: ['start-reflection', 'stop-reflection'],
    setup(props) {
        const showInterventionSettings = ref(false)
        const showProgressNotification = ref(false)
        const progressNotificationText = ref('')
        let progressNotificationTimer = null
        
        const interventionSettings = ref({
            idle_intervention_enabled: true,
            idle_intervention_delay: 5,
            progress_check_enabled: false,
            progress_check_interval: 45
        })
        
        const showProgressCheckNotification = (message) => {
            progressNotificationText.value = message
            showProgressNotification.value = true
            
            // Clear any existing timer but don't set auto-dismiss
            if (progressNotificationTimer) {
                clearTimeout(progressNotificationTimer)
                progressNotificationTimer = null
            }
        }
        
        const dismissProgressNotification = () => {
            showProgressNotification.value = false
            if (progressNotificationTimer) {
                clearTimeout(progressNotificationTimer)
                progressNotificationTimer = null
            }
        }
        
        // Manual progress check functionality
        const isCheckingProgress = ref(false)
        
        const triggerManualProgressCheck = async () => {
            if (!props.roomId || isCheckingProgress.value) {
                return
            }
            
            try {
                isCheckingProgress.value = true
                console.log('📊 Triggering manual progress check for room:', props.roomId)
                
                const response = await fetch(`/api/manual-progress-check/${props.roomId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                })
                
                const data = await response.json()
                console.log('📊 Manual progress check response:', data)
                
                if (data.success) {
                    // The notification will be received via socket, no need to show it here
                    console.log('📊 Manual progress check completed successfully')
                } else {
                    console.error('Failed to trigger manual progress check:', data.error)
                    // Show error notification
                    showProgressCheckNotification(`Error: ${data.error}`)
                }
                
            } catch (error) {
                console.error('Error triggering manual progress check:', error)
                showProgressCheckNotification('Error checking progress. Please try again.')
            } finally {
                isCheckingProgress.value = false
            }
        }
        
        const loadInterventionSettings = async () => {
            try {
                const response = await fetch('/api/intervention-settings')
                const data = await response.json()
                if (data.success) {
                    interventionSettings.value = data.settings
                }
            } catch (error) {
                console.error('Failed to load intervention settings:', error)
            }
        }
        
        const handleSaveInterventionSettings = async (newSettings) => {
            try {
                const response = await fetch('/api/intervention-settings', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ settings: newSettings })
                })
                
                const data = await response.json()
                if (data.success) {
                    interventionSettings.value = data.settings
                    showInterventionSettings.value = false
                } else {
                    console.error('Failed to save intervention settings:', data.error)
                    alert('Failed to save settings: ' + data.error)
                }
            } catch (error) {
                console.error('Failed to save intervention settings:', error)
                alert('Failed to save settings. Please try again.')
            }
        }
        
        onMounted(() => {
            loadInterventionSettings()
            
            // Set up socket listener for progress check notifications
            if (props.socket) {
                props.socket.on('progress_check_notification', (data) => {
                    console.log('📊 Progress check notification received:', data)
                    showProgressCheckNotification(data.content)
                })
            }
        })
        
        // Cleanup on unmount
        onUnmounted(() => {
            if (progressNotificationTimer) {
                clearTimeout(progressNotificationTimer)
            }
            if (props.socket) {
                props.socket.off('progress_check_notification')
            }
        })
        
        return {
            showInterventionSettings,
            interventionSettings,
            handleSaveInterventionSettings,
            showProgressNotification,
            progressNotificationText,
            showProgressCheckNotification,
            dismissProgressNotification,
            isCheckingProgress,
            triggerManualProgressCheck
        }
    }
})
</script>

<style scoped>
.ai-agent-status {
    background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
    border: 1px solid #0ea5e9;
    border-radius: 12px;
    padding: 1rem;
    box-shadow: 0 2px 8px rgba(14, 165, 233, 0.1);
    width: 100%;
    position: relative;
    z-index: 10;
    overflow: visible;
}

.ai-indicator {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
}

.ai-avatar {
    width: 2.5rem;
    height: 2.5rem;
    background: linear-gradient(135deg, #10b981, #059669);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
    position: relative;
}

/* Progress Check Notification Bubble */
.progress-notification-bubble {
    position: fixed;
    top: 20px;
    right: 20px;
    background: white;
    border: 2px solid #007acc;
    border-radius: 12px;
    padding: 12px 16px;
    box-shadow: 0 4px 12px rgba(0, 122, 204, 0.15);
    z-index: 10000;
    max-width: 300px;
    cursor: pointer;
    backdrop-filter: blur(8px);
}

.progress-content {
    display: flex;
    align-items: center;
    gap: 8px;
}

.progress-icon {
    font-size: 16px;
    flex-shrink: 0;
}

.progress-text {
    color: #333;
    font-size: 14px;
    line-height: 1.4;
    flex: 1;
}

.progress-dismiss {
    color: #666;
    font-size: 18px;
    font-weight: bold;
    cursor: pointer;
    padding: 0 4px;
    border-radius: 4px;
    transition: background-color 0.2s;
}

.progress-dismiss:hover {
    background-color: rgba(0, 122, 204, 0.1);
}

/* Animation for progress notification */
.progress-notification-enter-active,
.progress-notification-leave-active {
    transition: all 0.3s ease;
}

.progress-notification-enter-from {
    opacity: 0;
    transform: translateY(-20px) scale(0.9);
}

.progress-notification-leave-to {
    opacity: 0;
    transform: translateY(-20px) scale(0.9);
}

/* Animation for progress notification */
.progress-notification-enter-active {
    transition: all 0.3s ease;
}

.progress-notification-leave-active {
    transition: all 0.2s ease;
}

.progress-notification-enter-from {
    opacity: 0;
    transform: scale(0.8) translateY(-10px);
}

.progress-notification-leave-to {
    opacity: 0;
    transform: scale(0.9) translateY(-5px);
}

.ai-emoji {
    font-size: 1.25rem;
}

.ai-info {
    flex: 1;
}

.ai-name {
    font-weight: 600;
    color: #0f172a;
    font-size: 0.875rem;
    margin-bottom: 0.25rem;
}

.ai-status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.75rem;
    color: #10b981;
    font-weight: 500;
}

.status-dot {
    width: 0.5rem;
    height: 0.5rem;
    background: #10b981;
    border-radius: 50%;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% {
        opacity: 1;
        transform: scale(1);
    }
    50% {
        opacity: 0.7;
        transform: scale(1.1);
    }
}

.status-dot.reflection-mode {
    background: #f59e0b;
    animation: pulse-reflection 2s infinite;
}

@keyframes pulse-reflection {
    0%, 100% {
        opacity: 1;
        transform: scale(1);
    }
    50% {
        opacity: 0.7;
        transform: scale(1.2);
    }
}

.action-buttons {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.settings-button {
    background: linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 100%);
    color: #475569;
    border: none;
    border-radius: 6px;
    padding: 0.25rem 0.5rem;
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s ease;
    white-space: nowrap;
    box-shadow: 0 2px 4px rgba(148, 163, 184, 0.2);
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 2rem;
    height: 1.75rem;
}

.settings-button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(148, 163, 184, 0.3);
    background: linear-gradient(135deg, #cbd5e1 0%, #94a3b8 100%);
}

.ai-description {
    border-top: 1px solid rgba(14, 165, 233, 0.2);
    padding-top: 0.75rem;
}

.ai-desc-text {
    font-size: 0.75rem;
    color: #475569;
    line-height: 1.4;
    margin: 0;
}

.reflection-button-small {
    background: linear-gradient(135deg, #7dd3fc 0%, #38bdf8 100%);
    color: #1e293b;
    border: none;
    border-radius: 6px;
    padding: 0.25rem 0.5rem;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    white-space: nowrap;
    box-shadow: 0 2px 4px rgba(125, 211, 252, 0.3);
}

.reflection-button-small:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(125, 211, 252, 0.4);
}

.reflection-button-small:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
}

.reflection-stop-button {
    background: linear-gradient(135deg, #fca5a5 0%, #f87171 100%);
    color: #1e293b;
    border: none;
    border-radius: 6px;
    padding: 0.25rem 0.5rem;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    white-space: nowrap;
    box-shadow: 0 2px 4px rgba(252, 165, 165, 0.3);
}

.reflection-stop-button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(252, 165, 165, 0.4);
}

.progress-check-button {
    background: #ffffff;
    color: #0ea5e9;
    border: 1px solid #0ea5e9;
    border-radius: 6px;
    padding: 0.25rem 0.5rem;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    white-space: nowrap;
    box-shadow: 0 2px 4px rgba(14, 165, 233, 0.2);
}

.progress-check-button:hover:not(:disabled) {
    background: #f0f9ff;
    border-color: #0284c7;
    color: #0284c7;
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(14, 165, 233, 0.3);
}

.progress-check-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
    background: #f8fafc;
    color: #94a3b8;
    border-color: #cbd5e1;
}
</style>
