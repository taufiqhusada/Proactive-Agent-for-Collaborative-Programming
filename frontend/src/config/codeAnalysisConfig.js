// Configuration for proactive code analysis
export const codeAnalysisConfig = {
  // Analysis triggers
  triggers: {
    minLines: 3,
    minCharacters: 50,
    typingPauseMs: 2000,
    confirmationDelayMs: 1000,
    cooldownMs: 5000,
    maxAnalysisFrequency: 6 // Maximum analyses per minute
  },
  
  // Issue detection patterns
  patterns: {
    structuralElements: [
      'function', 'class', 'if', 'for', 'while', 'try', 'def', 'async'
    ],
    riskPatterns: {
      python: [
        /eval\s*\(/,
        /exec\s*\(/,
        /input\s*\(/,
        /os\.system\s*\(/,
        /subprocess\.(call|run|Popen)/,
        /pickle\.loads?\s*\(/,
        /yaml\.load\s*\(/
      ],
      javascript: [
        /eval\s*\(/,
        /innerHTML\s*=/,
        /document\.write\s*\(/,
        /setTimeout\s*\(\s*["'`]/,
        /setInterval\s*\(\s*["'`]/,
        /new\s+Function\s*\(/
      ]
    }
  },
  
  // UI configuration
  ui: {
    panelPosition: 'right',
    autoDismissMs: 15000,
    showConfidence: true,
    showLineNumbers: true,
    enableSuggestionHistory: true
  },
  
  // Analysis types to enable
  analysisTypes: {
    security: true,
    performance: true,
    bugRisk: true,
    bestPractices: true,
    readability: true,
    logic: true
  }
}

// Helper function to check if code block meets analysis criteria
export function shouldAnalyzeCodeBlock(codeBlock, config = codeAnalysisConfig) {
  const { triggers } = config
  
  // Size check
  const lines = codeBlock.code.split('\n').filter(line => line.trim().length > 0)
  const chars = codeBlock.code.replace(/\s/g, '').length
  
  if (lines.length < triggers.minLines && chars < triggers.minCharacters) {
    return false
  }
  
  // Structure check
  const hasStructure = triggers.structuralElements.some(element => {
    const pattern = new RegExp(`\\b${element}\\b`, 'i')
    return pattern.test(codeBlock.code)
  })
  
  if (!hasStructure) {
    return false
  }
  
  return true
}

// Helper function to detect language-specific risk patterns
export function detectRiskPatterns(code, language = 'python') {
  const patterns = codeAnalysisConfig.patterns.riskPatterns[language] || []
  return patterns.filter(pattern => pattern.test(code))
}

export default codeAnalysisConfig
