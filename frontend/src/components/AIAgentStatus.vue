<template>
    <div class="ai-agent-status">
        <div class="ai-indicator">
            <div class="ai-avatar">
                <span class="ai-emoji">🤖</span>
            </div>
            <div class="ai-info">
                <div class="ai-name">CodeBob</div>
                <div class="ai-status">
                    <span class="status-dot"></span>
                    AI Assistant Active
                </div>
            </div>
            <!-- Reflection Button -->
            <button 
                @click="$emit('start-reflection')"
                :disabled="reflectionActive"
                class="reflection-button-small"
                title="Start learning reflection"
            >
                🎓 Reflect
            </button>
        </div>
        <div class="ai-description">
            <p class="ai-desc-text">
                CodeBob is listening and can jump in to help!
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
    emits: ['start-reflection']
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
</style>
