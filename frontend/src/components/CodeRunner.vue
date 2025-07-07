<template>
  <div class="code-runner">
    <!-- Run Button -->
    <div class="runner-header">
      <button 
        @click="runCode" 
        :disabled="isRunning"
        class="run-button"
        :class="{ 'running': isRunning }"
      >
        <span class="run-icon">{{ isRunning ? '⏳' : '▶️' }}</span>
        {{ isRunning ? 'Running...' : 'Run Code' }}
      </button>
      
      <div class="runner-info">
        <span class="language-info">{{ languageDisplayName }}</span>
        <span class="execution-time" v-if="lastExecutionTime">
          {{ lastExecutionTime }}ms
        </span>
      </div>
    </div>

    <!-- Output Terminal -->
    <div class="terminal-container" v-if="showOutput">
      <div class="terminal-header">
        <div class="terminal-title">
          <span class="terminal-icon">🖥️</span>
          Output
        </div>
        <div class="terminal-controls">
          <button @click="clearOutput" class="clear-btn" title="Clear output">
            🗑️
          </button>
          <button @click="toggleTerminal" class="minimize-btn" title="Minimize">
            ➖
          </button>
        </div>
      </div>
      
      <div class="terminal-output" ref="terminalOutput">
        <div v-if="!output && !error" class="terminal-placeholder">
          Click "Run Code" to execute your program...
        </div>
        
        <!-- Program Output -->
        <div v-if="output" class="output-section">
          <div class="output-header">
            <span class="output-label">Output:</span>
          </div>
          <pre class="output-text">{{ output }}</pre>
        </div>
        
        <!-- Error Output -->
        <div v-if="error" class="error-section">
          <div class="error-header">
            <span class="error-icon">❌</span>
            <span class="error-label">Error:</span>
          </div>
          <pre class="error-text">{{ error }}</pre>
        </div>
        
        <!-- Execution Info -->
        <div v-if="executionInfo" class="execution-info">
          <span class="info-icon">ℹ️</span>
          {{ executionInfo }}
        </div>

        <!-- NEW: AI Analysis Section -->
        <div v-if="aiAnalysis" class="ai-analysis-section">
          <div class="analysis-header">
            <div class="analysis-title-group">
              <span class="analysis-icon">🔍</span>
              <span class="analysis-title">AI Analysis</span>
            </div>
            <button 
              @click="requestDetailedHelp" 
              class="more-help-btn"
            >
              Get Detailed Help
            </button>
          </div>
          <div :class="['analysis-content', aiAnalysis.type]">
            {{ aiAnalysis.message }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CodeRunner',
  
  emits: ['chat-message'],
  
  props: {
    code: {
      type: String,
      required: true
    },
    language: {
      type: String,
      required: true
    },
    roomId: {
      type: String,
      default: null
    },
    socket: {
      type: Object,
      default: null
    },
    currentUserId: {
      type: String,
      default: null
    }
  },
  
  data() {
    return {
      isRunning: false,
      output: '',
      error: '',
      showOutput: false,
      lastExecutionTime: null,
      executionInfo: '',
      aiAnalysis: null  // NEW: Store AI analysis for execution panel
    }
  },

  mounted() {
    this.setupSocketListeners();
  },
  
  computed: {
    languageDisplayName() {
      const languages = {
        'python': '🐍 Python',
        'javascript': '🚀 JavaScript',
        'java': '☕ Java',
        'cpp': '⚡ C++',
        'c': '🔧 C'
      };
      return languages[this.language] || this.language;
    }
  },
  
  methods: {
    setupSocketListeners() {
      if (this.socket) {
        // Listen for AI analysis results
        this.socket.on('execution_analysis', (data) => {
          if (data.analysis) {
            this.aiAnalysis = data.analysis;
            console.log('📊 Received AI analysis:', data.analysis);
          }
        });
      }
    },

    requestDetailedHelp() {
      // Send a message to chat requesting detailed help
      if (this.socket && this.roomId && this.aiAnalysis) {
        const message = {
          room: this.roomId,
          content: '@ai Can you provide help with my code execution issue?',
          username: 'User',
          userId: this.currentUserId || 'user_' + Date.now(),
          timestamp: new Date().toISOString()
        };

        // Emit to parent component to add to local chat
        this.$emit('chat-message', message);
        
        // Send to socket for other users
        this.socket.emit('chat_message', message);
      }
    },

    async runCode() {
      if (!this.code.trim()) {
        this.error = 'No code to execute';
        this.showOutput = true;
        return;
      }
      
      this.isRunning = true;
      this.output = '';
      this.error = '';
      this.executionInfo = '';
      this.showOutput = true;
      this.aiAnalysis = null;  // Clear previous AI analysis
      
      const startTime = Date.now();
      
      try {
        console.log('🚀 Running code:', this.code);
        
        const response = await fetch('/api/run-code', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            code: this.code,
            language: this.language,
            room_id: this.roomId  // Include room_id for AI validation
          })
        });
        
        const result = await response.json();
        const executionTime = Date.now() - startTime;
        this.lastExecutionTime = executionTime;
        
        if (response.ok) {
          this.output = result.output || '';
          this.error = result.error || '';
          this.executionInfo = `Executed in ${executionTime}ms`;
          
          if (result.exitCode !== 0) {
            this.executionInfo += ` (Exit code: ${result.exitCode})`;
          }
          
          // Emit code execution event to room (for real-time collaboration)
          if (this.roomId && this.socket) {
            this.socket.emit('code_execution', {
              room: this.roomId,
              code: this.code,
              language: this.language,
              result: result
            });
          }
        } else {
          this.error = result.error || 'Execution failed';
        }
        
        // Scroll to bottom of output
        this.$nextTick(() => {
          if (this.$refs.terminalOutput) {
            this.$refs.terminalOutput.scrollTop = this.$refs.terminalOutput.scrollHeight;
          }
        });
        
      } catch (error) {
        console.error('❌ Code execution error:', error);
        this.error = `Network error: ${error.message}`;
        this.executionInfo = 'Execution failed';
      } finally {
        this.isRunning = false;
      }
    },
    
    clearOutput() {
      this.output = '';
      this.error = '';
      this.executionInfo = '';
      this.lastExecutionTime = null;
    },
    
    toggleTerminal() {
      this.showOutput = !this.showOutput;
    }
  }
}
</script>

<style scoped>
.code-runner {
  border-top: 1px solid #e1e5e9;
  background: #f8f9fa;
}

.runner-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #ffffff;
  border-bottom: 1px solid #e9ecef;
}

.run-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
  color: #212529;
  border: 1px solid #0ea5e9;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(14, 165, 233, 0.1);
}

.run-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #e0f2fe, #bae6fd);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(14, 165, 233, 0.2);
}

.run-button:disabled {
  background: #6c757d;
  cursor: not-allowed;
  transform: none;
}

.run-button.running {
  background: #ffc107;
  color: #212529;
}

.run-icon {
  font-size: 12px;
}

.runner-info {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 14px;
  color: #6c757d;
}

.language-info {
  font-weight: 500;
}

.execution-time {
  background: #e9ecef;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.terminal-container {
  background: #f8f9fa;
  color: #495057;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', Consolas, monospace;
  font-size: 13px;
  line-height: 1.4;
  border: 1px solid #e9ecef;
  border-radius: 6px;
}

.terminal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #ffffff;
  border-bottom: 1px solid #e9ecef;
  border-radius: 6px 6px 0 0;
}

.terminal-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: #495057;
}

.terminal-icon {
  font-size: 14px;
}

.terminal-controls {
  display: flex;
  gap: 8px;
}

.clear-btn, .minimize-btn {
  background: none;
  border: 1px solid #dee2e6;
  color: #6c757d;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  transition: all 0.2s;
}

.clear-btn:hover, .minimize-btn:hover {
  background: #e9ecef;
  border-color: #adb5bd;
}

.terminal-output {
  padding: 12px;
  max-height: 300px;
  overflow-y: auto;
  min-height: 150px;
  background: #ffffff;
}

.terminal-placeholder {
  color: #6c757d;
  font-style: italic;
  text-align: center;
  padding: 40px 20px;
}

.output-section, .error-section {
  margin-bottom: 12px;
}

.output-header, .error-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-weight: 500;
}

.output-icon, .error-icon {
  font-size: 14px;
}

.output-label {
  color: #0d6efd;
}

.error-label {
  color: #dc3545;
}

.output-text {
  background: #f8f9fa;
  padding: 8px 12px;
  border-radius: 4px;
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  color: #495057;
  border-left: 3px solid #0d6efd;
}

.error-text {
  background: #f8f9fa;
  padding: 8px 12px;
  border-radius: 4px;
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  color: #dc3545;
  border-left: 3px solid #dc3545;
}

.execution-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #6c757d;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #e9ecef;
}

.info-icon {
  font-size: 12px;
}

/* AI Analysis Section */
.ai-analysis-section {
  margin-top: 12px;
  border: 1px solid #e3f2fd;
  border-radius: 6px;
  background: linear-gradient(135deg, #f0f9ff, #e3f2fd);
  overflow: hidden;
}

.analysis-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: linear-gradient(135deg, #e3f2fd, #bbdefb);
  border-bottom: 1px solid #e3f2fd;
}

.analysis-title-group {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
  color: #1565c0;
}

.analysis-icon {
  font-size: 14px;
}

.analysis-title {
  font-size: 13px;
}

.analysis-content {
  padding: 10px 12px;
  font-size: 13px;
  color: #424242;
  line-height: 1.4;
  word-wrap: break-word;
  overflow-wrap: break-word;
  white-space: normal;
}

.analysis-content.error {
  color: #d32f2f;
  background: linear-gradient(135deg, #fff5f5, #ffebee);
}

.analysis-content.warning {
  color: #ef6c00;
  background: linear-gradient(135deg, #fffaf0, #fff8e1);
}

.more-help-btn {
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 500;
  color: #1565c0;
  background: white;
  border: 1px solid #1565c0;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.more-help-btn:hover {
  background: #1565c0;
  color: white;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(21, 101, 192, 0.2);
}

/* Scrollbar styling for terminal */
.terminal-output::-webkit-scrollbar {
  width: 6px;
}

.terminal-output::-webkit-scrollbar-track {
  background: #f8f9fa;
}

.terminal-output::-webkit-scrollbar-thumb {
  background: #dee2e6;
  border-radius: 3px;
}

.terminal-output::-webkit-scrollbar-thumb:hover {
  background: #adb5bd;
}
</style>
