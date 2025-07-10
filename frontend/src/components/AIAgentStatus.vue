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
        </div>            <div class="ai-description">
                <p class="ai-desc-text">
                    {{ reflectionActive 
                        ? 'Bob is guiding your learning reflection. You can exit anytime!' 
                        : 'Hi, I am Bob, your proactive AI teammate. I am listening and can jump in to help!' }}
                </p>
            </div>
    </div>
</template>

<script>
import { defineComponent } from 'vue'

export default defineComponent({
    name: 'AIAgentStatus',
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
    emits: ['start-reflection', 'stop-reflection']
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
    margin-left: 0.5rem;
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
    margin-left: 0.5rem;
}

.reflection-stop-button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(252, 165, 165, 0.4);
}
</style>
