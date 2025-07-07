<template>
  <div v-if="visible" class="scaffolding-panel">
    <div class="scaffolding-overlay" @click="$emit('dismissed')"></div>
    <div class="scaffolding-content">
      <div class="scaffolding-header">
        <div class="scaffolding-title">
          <span class="scaffolding-icon">🏗️</span>
          <h3>Code Scaffolding Available</h3>
          <span class="difficulty-badge" :class="difficultyClass">
            {{ suggestion?.template?.difficulty || 'beginner' }}
          </span>
        </div>
        <button class="close-btn" @click="$emit('dismissed')" title="Close">
          <span>×</span>
        </button>
      </div>
      
      <div class="scaffolding-body">
        <div class="suggestion-info">
          <p class="hint">{{ suggestion?.hint }}</p>
          <div class="template-info">
            <strong>Template:</strong> {{ suggestion?.template?.description }}
          </div>
          <div class="original-comment">
            <strong>Your comment:</strong>
            <code>{{ suggestion?.originalComment }}</code>
          </div>
        </div>
        
        <div class="scaffolding-preview">
          <h4>Generated Scaffolding:</h4>
          <pre class="code-preview"><code>{{ suggestion?.scaffoldingCode }}</code></pre>
        </div>
        
        <div class="scaffolding-actions">
          <button 
            class="btn btn-primary" 
            @click="$emit('apply-scaffolding', suggestion)"
            title="Replace comment with scaffolding">
            <span class="btn-icon">✨</span>
            Apply Scaffolding
          </button>
          <button 
            class="btn btn-secondary" 
            @click="$emit('preview-scaffolding', suggestion)"
            title="View in larger window">
            <span class="btn-icon">👁️</span>
            Preview
          </button>
          <button 
            class="btn btn-outline" 
            @click="$emit('dismissed')"
            title="Close without applying">
            <span class="btn-icon">❌</span>
            Dismiss
          </button>
        </div>
        
        <div class="scaffolding-tips">
          <h5>💡 Tips:</h5>
          <ul>
            <li>Fill in the blanks (<code>___</code>) with your code</li>
            <li>Read the TODO comments for guidance</li>
            <li>Consider edge cases and error handling</li>
            <li>Ask your pair programming partner for help!</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'ScaffoldingPanel',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    suggestion: {
      type: Object,
      default: null
    }
  },
  emits: ['dismissed', 'apply-scaffolding', 'preview-scaffolding'],
  setup(props) {
    const difficultyClass = computed(() => {
      const difficulty = props.suggestion?.template?.difficulty || 'beginner'
      return `difficulty-${difficulty}`
    })
    
    return {
      difficultyClass
    }
  }
}
</script>

<style scoped>
.scaffolding-panel {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.scaffolding-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
}

.scaffolding-content {
  position: relative;
  background: white;
  border-radius: 12px;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.15);
  max-width: 800px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.scaffolding-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem 1rem 2rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px 12px 0 0;
}

.scaffolding-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.scaffolding-icon {
  font-size: 1.5rem;
}

.scaffolding-title h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
}

.difficulty-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.difficulty-beginner {
  background: rgba(34, 197, 94, 0.2);
  color: #16a34a;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.difficulty-intermediate {
  background: rgba(251, 191, 36, 0.2);
  color: #d97706;
  border: 1px solid rgba(251, 191, 36, 0.3);
}

.difficulty-advanced {
  background: rgba(239, 68, 68, 0.2);
  color: #dc2626;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.close-btn {
  background: none;
  border: none;
  color: white;
  font-size: 2rem;
  cursor: pointer;
  padding: 0;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.scaffolding-body {
  padding: 2rem;
}

.suggestion-info {
  margin-bottom: 1.5rem;
}

.hint {
  font-size: 1rem;
  color: #4a5568;
  margin-bottom: 1rem;
  line-height: 1.6;
}

.template-info, .original-comment {
  margin-bottom: 0.75rem;
  font-size: 0.9rem;
  color: #2d3748;
}

.original-comment code {
  background: #f7fafc;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  color: #2d3748;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  border: 1px solid #e2e8f0;
}

.scaffolding-preview {
  margin-bottom: 1.5rem;
}

.scaffolding-preview h4 {
  margin: 0 0 0.75rem 0;
  color: #2d3748;
  font-size: 1rem;
  font-weight: 600;
}

.code-preview {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1rem;
  margin: 0;
  overflow-x: auto;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  color: #2d3748;
  max-height: 300px;
  overflow-y: auto;
}

.scaffolding-actions {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  border-radius: 8px;
  border: none;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
}

.btn-secondary {
  background: #4a5568;
  color: white;
}

.btn-secondary:hover {
  background: #2d3748;
  transform: translateY(-1px);
}

.btn-outline {
  background: transparent;
  color: #4a5568;
  border: 2px solid #e2e8f0;
}

.btn-outline:hover {
  background: #f7fafc;
  border-color: #cbd5e0;
}

.btn-icon {
  font-size: 1rem;
}

.scaffolding-tips {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 8px;
  padding: 1rem;
}

.scaffolding-tips h5 {
  margin: 0 0 0.5rem 0;
  color: #0369a1;
  font-size: 0.875rem;
  font-weight: 600;
}

.scaffolding-tips ul {
  margin: 0;
  padding-left: 1.25rem;
  color: #0369a1;
}

.scaffolding-tips li {
  margin-bottom: 0.25rem;
  font-size: 0.875rem;
  line-height: 1.4;
}

.scaffolding-tips code {
  background: rgba(3, 105, 161, 0.1);
  padding: 0.125rem 0.25rem;
  border-radius: 3px;
  font-size: 0.8rem;
}

/* Responsive design */
@media (max-width: 768px) {
  .scaffolding-panel {
    padding: 1rem;
  }
  
  .scaffolding-header {
    padding: 1rem;
    flex-direction: column;
    gap: 0.5rem;
    align-items: flex-start;
  }
  
  .scaffolding-title {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
  
  .scaffolding-body {
    padding: 1rem;
  }
  
  .scaffolding-actions {
    flex-direction: column;
  }
  
  .btn {
    justify-content: center;
  }
}
</style>
