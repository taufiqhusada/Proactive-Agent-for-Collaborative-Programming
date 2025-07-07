<template>
  <!-- Results panel - only show when issues are found -->
  <div 
    v-if="showIssues" 
    class="code-issue-panel"
    :style="panelPosition"
  >
    <!-- Close button -->
    <button @click="dismissPanel" class="close-btn">×</button>

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
    }
  },    data() {
    return {
      showIssues: false,
      issues: [],
      panelPosition: { top: '100px', right: '20px' },
      analysisInProgress: false
    }
  },
  
  watch: {
    visible(newVal) {
      console.log('🔍 CodeIssuePanel visibility changed:', newVal)
      // Don't show panel immediately - wait for analysis results
      if (!newVal) {
        this.showIssues = false;
      }
      // If newVal is true, check if we have a code block to analyze
      if (newVal && this.codeBlock) {
        console.log('🚀 Starting code analysis (visibility changed)...')
        this.analyzeCodeBlock(this.codeBlock);
      }
    },
    
    codeBlock(newBlock) {
      console.log('📝 CodeIssuePanel received code block:', newBlock)
      if (newBlock && this.visible) {
        console.log('🚀 Starting code analysis (code block changed)...')
        this.analyzeCodeBlock(newBlock);
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
    async analyzeCodeBlock(codeBlock) {
      console.log('🔬 analyzeCodeBlock called with:', codeBlock)
      
      if (this.analysisInProgress) {
        console.log('⏳ Analysis already in progress, skipping...')
        return;
      }
      
      this.analysisInProgress = true;
      
      console.log('🚀 Starting API call to backend...')
      
      try {
        const response = await fetch('/api/analyze-code-block', {
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
            problemContext: codeBlock.problemContext || null
          })
        });
        
        console.log('📡 API response status:', response.status)
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }
        
        const analysis = await response.json();
        console.log('📊 Analysis result:', analysis)
        
        if (analysis.issues && analysis.issues.length > 0) {
          console.log('🎯 Issues found, displaying panel...')
          this.displayIssues(analysis.issues, codeBlock);
        } else {
          console.log('✅ No issues found - staying hidden')
          // Don't show anything if no issues
        }
      } catch (error) {
        console.error('💥 Error analyzing code block:', error);
      } finally {
        this.analysisInProgress = false;
      }
    },
    
    displayIssues(issues, codeBlock) {
      this.issues = issues;
      this.positionPanel(codeBlock);
      this.showIssues = true;
      
      // Don't auto-dismiss - let user close manually
    },
    
    positionPanel(codeBlock) {
      // Position panel relative to the code block
      const viewport = {
        width: window.innerWidth,
        height: window.innerHeight
      };
      
      // Try to position on the right side first
      let top = Math.max(this.editorPosition.top + 50, 50);
      let right = 20;
      
      // Calculate panel position
      if (viewport.width < 800) {
        right = 'auto';
        this.panelPosition = {
          position: 'fixed',
          top: top + 'px',
          left: '20px',
          right: 'auto',
          zIndex: 1000
        };
      } else {
        this.panelPosition = {
          position: 'fixed',
          top: top + 'px',
          right: right + 'px',
          zIndex: 1000
        };
      }
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
  padding: 16px;
  padding-top: 40px; /* Space for close button */
}

.close-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #6c757d;
  padding: 4px;
  border-radius: 4px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
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
