<template>
  <!-- Results panel - only show when issues are found -->
  <div 
    v-if="showIssues" 
    class="code-issue-panel"
    :class="{ 'dragging': isDragging }"
    :style="panelPosition"
  >
    <!-- Draggable header -->
    <div 
      class="panel-header"
      @mousedown="startDragging"
      ref="dragHandle"
    >
      <div class="panel-title">
        <span class="panel-icon">🔍</span>
        Code Analysis
      </div>
      <button @click="dismissPanel" class="close-btn">×</button>
    </div>

    <!-- Issues List -->
    <div class="issues-container">
      <div 
        v-for="issue in issues" 
        :key="issue.id"
        class="issue-item"
        :class="issue.severity"
        @click="highlightIssueInCode(issue)"
      >
        <!-- Issue Type & Severity -->
        <div class="issue-header">
          <span class="issue-icon">{{ getIssueIcon(issue.type) }}</span>
          <span class="issue-type">{{ issue.type }}</span>
          <span class="severity-badge" :class="issue.severity">{{ issue.severity }}</span>
        </div>

        <!-- Issue Description -->
        <div class="issue-description">
          <p class="issue-title">{{ issue.title }}</p>
          <p class="issue-details">{{ issue.description }}</p>
        </div>

        <!-- Code Reference -->
        <div class="code-reference">
          <span class="line-number">Lines {{ getLineRange(issue) }}</span>
          <code class="problematic-code">{{ issue.codeSnippet }}</code>
        </div>

        <!-- Suggested Fix -->
        <div v-if="issue.suggestedFix" class="suggested-fix">
          <div class="fix-header">
            <span class="fix-icon">💡</span>
            <span class="fix-label">Hint:</span>
          </div>
          <div class="fix-content">
            <p class="fix-description">{{ issue.suggestedFix.description }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CodeIssuePanel',
  
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    codeBlock: {
      type: Object,
      default: null
    },
    editorPosition: {
      type: Object,
      default: () => ({ top: 100, left: 0 })
    },
    socket: {
      type: Object,
      default: null
    },
    roomId: {
      type: String,
      default: ''
    },
    currentUserId: {
      type: String,
      default: ''
    }
  },    data() {
    return {
      showIssues: false,
      issues: [],
      analysisInProgress: false,
      // Dragging state
      isDragging: false,
      dragOffset: { x: 0, y: 0 },
      currentPosition: { x: window.innerWidth - 420, y: 100 } // Default position
    }
  },
  
  computed: {
    panelPosition() {
      return {
        position: 'fixed',
        left: `${this.currentPosition.x}px`,
        top: `${this.currentPosition.y}px`,
        right: 'auto', // Override the right positioning
        zIndex: this.isDragging ? 1001 : 1000 // Higher z-index when dragging
      }
    }
  },
  
  watch: {
    visible(newVal) {
      console.log('🔍 CodeIssuePanel visibility changed:', newVal)
      // Don't show panel immediately - wait for analysis results
      if (!newVal) {
        this.showIssues = false;
      }
      // Only trigger analysis for local (non-remote) code blocks
      if (newVal && this.codeBlock && !this.codeBlock.isRemoteAnalysis) {
        console.log('🚀 Starting code analysis (visibility changed)...')
        this.analyzeCodeBlock(this.codeBlock);
      }
    },
    
    codeBlock(newBlock) {
      console.log('📝 CodeIssuePanel received code block:', newBlock)
      if (newBlock && this.visible) {
        if (newBlock.isRemoteAnalysis && newBlock.issues) {
          console.log('� Displaying remote analysis results directly')
          this.displayIssues(newBlock.issues, newBlock);
        } else if (!newBlock.isRemoteAnalysis) {
          console.log('� Starting local code analysis (code block changed)...')
          this.analyzeCodeBlock(newBlock);
        }
      }
    }
  },
  
  mounted() {
    console.log('🔧 CodeIssuePanel mounted with props:', {
      visible: this.visible,
      codeBlock: this.codeBlock,
      editorPosition: this.editorPosition
    });
    
    // If both visible and codeBlock are already set, start analysis
    if (this.visible && this.codeBlock) {
      console.log('🚀 Starting code analysis (mounted)...')
      this.analyzeCodeBlock(this.codeBlock);
    }
  },
  
  methods: {
    // Dragging functionality
    startDragging(event) {
      this.isDragging = true;
      this.dragOffset.x = event.clientX - this.currentPosition.x;
      this.dragOffset.y = event.clientY - this.currentPosition.y;
      
      // Add global event listeners
      document.addEventListener('mousemove', this.onDrag);
      document.addEventListener('mouseup', this.stopDragging);
      
      // Prevent text selection while dragging
      document.body.style.userSelect = 'none';
      event.preventDefault();
    },
    
    onDrag(event) {
      if (!this.isDragging) return;
      
      const newX = event.clientX - this.dragOffset.x;
      const newY = event.clientY - this.dragOffset.y;
      
      // Keep panel within viewport bounds
      const panelWidth = 400; // Width of the panel
      const panelHeight = 200; // Minimum height to keep visible
      
      const maxX = window.innerWidth - panelWidth;
      const maxY = window.innerHeight - panelHeight;
      
      this.currentPosition.x = Math.max(0, Math.min(newX, maxX));
      this.currentPosition.y = Math.max(0, Math.min(newY, maxY));
    },
    
    stopDragging() {
      this.isDragging = false;
      
      // Remove global event listeners
      document.removeEventListener('mousemove', this.onDrag);
      document.removeEventListener('mouseup', this.stopDragging);
      
      // Restore text selection
      document.body.style.userSelect = '';
    },
    
    async analyzeCodeBlock(codeBlock) {
      console.log('🔬 analyzeCodeBlock called with:', codeBlock)
      
      if (this.analysisInProgress) {
        console.log('⏳ Analysis already in progress, skipping...')
        return;
      }
      
      this.analysisInProgress = true;
      
      console.log('🚀 Triggering analysis via API call...')
      
      try {
        // Fire and forget - just trigger the analysis, don't wait for response
        fetch('/api/analyze-code-block', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            code: codeBlock.code,
            language: codeBlock.language || 'python',
            context: {
              startLine: codeBlock.startLine,
              endLine: codeBlock.endLine,
              cursorLine: codeBlock.cursorLine
            },
            problemContext: codeBlock.problemContext || null,
            roomId: this.roomId  // Include room ID for socket broadcasting
          })
        }).then(response => {
          console.log('📡 Analysis triggered, status:', response.status)
          if (!response.ok) {
            console.error('❌ Analysis API call failed:', response.status, response.statusText)
          }
        }).catch(error => {
          console.error('� Error triggering analysis:', error);
        }).finally(() => {
          this.analysisInProgress = false;
        });
        
        console.log('📡 Analysis request sent, waiting for socket results...')
        
      } catch (error) {
        console.error('💥 Error triggering analysis:', error);
        this.analysisInProgress = false;
      }
    },
    
    displayIssues(issues, codeBlock) {
      this.issues = issues;
      this.showIssues = true;
      
      // Determine the highest severity level to update line indicators
      const severityPriority = { 'high': 3, 'medium': 2, 'low': 1 };
      const highestSeverity = issues.reduce((highest, issue) => {
        const currentPriority = severityPriority[issue.severity] || 0;
        const highestPriority = severityPriority[highest] || 0;
        return currentPriority > highestPriority ? issue.severity : highest;
      }, 'medium');
      
      // Emit event to update line indicators with the appropriate severity
      this.$emit('issues-found', {
        codeBlock,
        issues,
        highestSeverity
      });
      
      // Note: Socket broadcasting is now handled directly by the backend
      // when the API call is made, so no need to emit socket events here
      
      // Don't auto-dismiss - let user close manually
    },
    
    getIssueIcon(type) {
      const icons = {
        'Security': '🔒',
        'Performance': '⚡',
        'Bug Risk': '🐛',
        'Best Practice': '✨',
        'Readability': '📖',
        'Logic': '🤔',
        'Syntax': '⚠️',
        'Code Review': '🔍'
      };
      return icons[type] || '💡';
    },

    getLineRange(issue) {
      // Get the code block range from the current analysis
      if (this.codeBlock && this.codeBlock.startLine && this.codeBlock.endLine) {
        const startLine = this.codeBlock.startLine;
        const endLine = this.codeBlock.endLine;
        return startLine === endLine ? `${startLine}` : `${startLine}-${endLine}`;
      }
      // Fallback to issue line
      return issue.line || '1';
    },
    
    highlightIssueInCode(issue) {
      // Emit event to parent to highlight the problematic line
      this.$emit('highlight-line', issue.line);
    },
    
    dismissPanel() {
      this.showIssues = false;
      this.$emit('dismissed');
    }
  },
  
  beforeUnmount() {
    // Clean up event listeners if component is destroyed while dragging
    document.removeEventListener('mousemove', this.onDrag);
    document.removeEventListener('mouseup', this.stopDragging);
    document.body.style.userSelect = '';
  }
}
</script>

<style scoped>
.code-issue-panel {
  position: fixed;
  width: 400px;
  max-height: 600px;
  background: #ffffff;
  border: 1px solid #e1e5e9;
  border-radius: 8px;
  box-shadow: 0 12px 32px rgba(0,0,0,0.15);
  overflow-y: auto;
  z-index: 1000;
  font-family: -apple-system, BlinkMacSystemFont, sans-serif;
  font-size: 14px;
  transition: box-shadow 0.2s ease;
}

.code-issue-panel.dragging {
  box-shadow: 0 20px 48px rgba(0,0,0,0.25);
  transition: none;
}

.panel-header {
  position: sticky;
  top: 0;
  background: #f8f9fa;
  border-bottom: 1px solid #e1e5e9;
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: move;
  user-select: none;
  border-radius: 8px 8px 0 0;
}

.panel-header:hover {
  background: #e9ecef;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #495057;
}

.remote-indicator {
  font-size: 12px;
  color: #007bff;
  font-weight: 400;
  background: #e7f3ff;
  padding: 2px 6px;
  border-radius: 3px;
  margin-left: 4px;
}

.panel-icon {
  font-size: 16px;
}

.issues-container {
  padding: 16px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: #6c757d;
  padding: 4px;
  border-radius: 4px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #dc3545;
  color: white;
}

.close-btn:hover {
  background: #e9ecef;
  color: #495057;
}

.issues-container {
  max-height: 400px;
  overflow-y: auto;
}

.issue-item {
  padding: 16px;
  border-bottom: 1px solid #f1f3f4;
  cursor: pointer;
  transition: background-color 0.2s;
}

.issue-item:hover {
  background: #f8f9fa;
}

.issue-item.high {
  border-left: 4px solid #dc3545;
}

.issue-item.medium {
  border-left: 4px solid #ffc107;
}

.issue-item.low {
  border-left: 4px solid #28a745;
}

.issue-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.issue-icon {
  font-size: 16px;
}

.issue-type {
  font-weight: 500;
  color: #495057;
}

.severity-badge {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
}

.severity-badge.high {
  background: #f8d7da;
  color: #721c24;
}

.severity-badge.medium {
  background: #fff3cd;
  color: #856404;
}

.severity-badge.low {
  background: #d4edda;
  color: #155724;
}

.issue-description {
  margin-bottom: 12px;
}

.issue-title {
  font-weight: 500;
  color: #212529;
  margin: 0 0 4px 0;
}

.issue-details {
  color: #6c757d;
  font-size: 13px;
  margin: 0;
  line-height: 1.4;
}

.code-reference {
  background: #f8f9fa;
  padding: 8px 12px;
  border-radius: 4px;
  margin-bottom: 12px;
}

.line-number {
  font-size: 12px;
  color: #6c757d;
  font-weight: 500;
}

.problematic-code {
  display: block;
  margin-top: 4px;
  background: #fff;
  padding: 4px 8px;
  border-radius: 3px;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-size: 12px;
  color: #d63384;
  border-left: 3px solid #dc3545;
}

.suggested-fix {
  background: #e7f3ff;
  padding: 12px;
  border-radius: 4px;
  margin-bottom: 12px;
}

.fix-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.fix-icon {
  font-size: 14px;
}

.fix-label {
  font-weight: 500;
  color: #0056b3;
}

.fix-description {
  color: #495057;
  font-size: 13px;
  margin: 0;
}

/* Responsive design */
@media (max-width: 768px) {
  .code-issue-panel {
    width: calc(100vw - 40px);
    max-width: 400px;
  }
}
</style>
