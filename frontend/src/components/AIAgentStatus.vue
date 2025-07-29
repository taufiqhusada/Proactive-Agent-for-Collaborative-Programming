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
                    {{ reflectionActive ? 'Reflection Mode Active' : 'AI Teammate Active' }}
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
                
                <!-- Reflection Toggle Button -->
                <button 
                    v-if="!reflectionActive"
                    @click="$emit('start-reflection')"
                    class="reflection-button-small"
                    title="Start learning reflection"
                >
                    🎓 Reflect
                </button>
                <button 
                    v-else
                    @click="$emit('stop-reflection')"
                    class="reflection-stop-button"
                    title="Stop reflection and return to normal mode"
                >
                    🎓 Exit Reflection
                </button>
            </div>
        </div>            <div class="ai-description">
                <p class="ai-desc-text">
                    {{ reflectionActive 
                        ? 'Bob is guiding your learning reflection. You can exit anytime!' 
                        : 'Hi, I\'m Bob, your proactive AI teammate. I\'m listening and can jump in to help!' }}
                </p>
            </div>
    </div>
    
    <!-- Intervention Settings Modal -->
    <InterventionSettingsModal 
        :isVisible="showInterventionSettings"
        :settings="interventionSettings"
        @close="showInterventionSettings = false"
        @save="handleSaveInterventionSettings"
    />
</template>

<script>
import { defineComponent, ref, onMounted } from 'vue'
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
        }
    },
    emits: ['start-reflection', 'stop-reflection'],
    setup() {
        const showInterventionSettings = ref(false)
        const interventionSettings = ref({
            idle_intervention_enabled: true,
            idle_intervention_delay: 5,
            progress_check_enabled: true,
            progress_check_interval: 30
        })
        
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
        })
        
        return {
            showInterventionSettings,
            interventionSettings,
            handleSaveInterventionSettings
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
</style>
