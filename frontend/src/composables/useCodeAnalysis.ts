import { ref, watch } from 'vue'
import { useCodeAnalysisSettings } from './useCodeAnalysisSettings'

export function useCodeAnalysis(code: any, selectedLanguage: any, currentProblem: any, socket: any, roomId: any, currentUserId: any, auth: any, view: any, isLocalUpdate: any, isReadOnly: any, showCodeAnalysisLineIndicators: any, clearCodeAnalysisLineIndicators: any) {
  // Get code analysis settings
  const { codeAnalysisSettings } = useCodeAnalysisSettings()
  
  // Code analysis state
  const showCodeAnalysis = ref(false)
  const currentCodeBlock = ref(null)
  const lastAnalyzedHash = ref(0)
  const analysisDebounceTimer = ref<any>(null)
  const userTypingTimer = ref<any>(null)
  const lastTypingTime = ref(0)
  
  // Enhanced detection state
  const consecutiveEnters = ref(0)
  const ENTER_THRESHOLD = 2

  const extractCurrentCodeBlock = (editor: any, cursor: any) => {
    const doc = editor.state.doc
    const line = cursor.line
    
    console.log('🔍 Extracting code block around line:', line + 1)
    
    // Get current line to understand the context
    const currentLineText = doc.line(line + 1).text
    const currentIndent = getIndentLevel(currentLineText)
    
    console.log('📍 Current line text:', currentLineText)
    console.log('📏 Current indent level:', currentIndent)
    
    let startLine = line
    let endLine = line
    
    // Strategy: Find the outermost logical block that contains the cursor
    // Look backwards to find the start of the complete logical structure
    let bestStartLine = line
    let bestStartIndent = currentIndent
    
    for (let i = line; i >= 0; i--) {
      const lineText = doc.line(i + 1).text
      const indent = getIndentLevel(lineText)
      
      // Skip empty lines
      if (lineText.trim() === '') continue
      
      // If we find a line that starts a block and has less indentation, it's a candidate
      if (isBlockStart(lineText) && indent < bestStartIndent) {
        bestStartLine = i
        bestStartIndent = indent
        console.log('🎯 Found outer block start at line:', i + 1, 'indent:', indent, 'text:', lineText)
      }
      
      // If we find a line with 0 indentation that's not a block start, stop looking
      if (indent === 0 && !isBlockStart(lineText)) {
        break
      }
    }
    
    startLine = bestStartLine
    
    // Find the end of the logical block
    // Look forwards until we find a line with same or less indentation as the start
    const startLineText = doc.line(startLine + 1).text
    const startIndent = getIndentLevel(startLineText)
    
    console.log('📍 Using start line:', startLine + 1, 'with indent:', startIndent)
    
    for (let i = startLine + 1; i < doc.lines; i++) {
      const lineText = doc.line(i + 1).text
      const indent = getIndentLevel(lineText)
      
      // If we find a non-empty line with less or equal indentation to start, that's our end
      if (lineText.trim() !== '' && indent <= startIndent) {
        endLine = i - 1 // End at the previous line
        console.log('🏁 Found block end at line:', i, 'due to dedent')
        break
      } else if (i === doc.lines - 1) {
        endLine = i
        console.log('🏁 Block extends to end of file')
        break
      } else {
        endLine = i // Keep extending the block
      }
    }
    
    // Extract code block
    const codeLines = []
    for (let i = startLine; i <= endLine; i++) {
      codeLines.push(doc.line(i + 1).text)
    }
    
    const extractedCode = codeLines.join('\n')
    console.log('📦 Extracted code block:')
    console.log(extractedCode)
    
    return {
      code: extractedCode,
      startLine: startLine + 1, // Convert to 1-based
      endLine: endLine + 1,
      cursorLine: line + 1,
      language: selectedLanguage.value
    }
  }
  
  const getIndentLevel = (lineText: any) => {
    const match = lineText.match(/^(\s*)/)
    return match ? match[1].length : 0
  }
  
  const isBlockStart = (lineText: any) => {
    const trimmed = lineText.trim()
    if (trimmed === '') return false
    
    const patterns = [
      // Function definitions
      /^\s*(def|function)\s+\w+.*:/,
      // Class definitions
      /^\s*class\s+\w+.*:/,
      // Control structures
      /^\s*(if|elif|else|for|while|try|except|finally|with)\s*.*:/,
      // Method definitions in classes
      /^\s*(public|private|protected|static)\s+\w+.*\{/,
      // JavaScript/Java function patterns
      /^\s*\w+\s*=\s*function.*\{/,
      /^\s*function\s+\w+.*\{/,
      // Lambda or arrow functions that start blocks
      /^\s*\w+\s*=\s*lambda.*:/,
      // Simple assignment that could start a logical block
      /^\s*\w+\s*=\s*\[/,  // Array assignment
      /^\s*\w+\s*=\s*\{/,  // Dict/Object assignment
      // Common algorithmic patterns
      /^\s*for\s+\w+\s+in\s+range\s*\(/,  // for i in range(...)
      /^\s*for\s+\w+\s+in\s+\w+/,        // for item in items
      /^\s*while\s+\w+/,                  // while condition
      /^\s*if\s+\w+/,                     // if condition
    ]
    return patterns.some(pattern => pattern.test(lineText))
  }
  
  const shouldAnalyzeCodeBlock = (codeBlock: any) => {
    console.log('🔍 Checking code block significance...')
    console.log('📊 Code:', codeBlock.code)
    console.log('📏 Code length:', codeBlock.code.length)
    
    // Check if block is significant enough to analyze
    const lines = codeBlock.code.split('\n').filter((line: any) => line.trim().length > 0)
    const chars = codeBlock.code.replace(/\s/g, '').length
    
    console.log('📋 Lines:', lines.length, 'Characters:', chars)
    
    // Relaxed size check for educational coding - either condition is enough
    if (lines.length < 5 && chars < 140) {
      console.log('❌ Failed size check: lines < 5 AND chars < 140')
      return false
    }
    
    // Skip structure check for simple educational tasks
    // Students might write simple algorithms that are still worth analyzing
    console.log('✅ Code block meets minimum size requirements')
    
    // Change check - only analyze if code actually changed
    const blockHash = hashCode(codeBlock.code.trim())
    console.log('🔗 Block hash:', blockHash, 'Last hash:', lastAnalyzedHash.value)
    
    if (blockHash === lastAnalyzedHash.value) {
      console.log('❌ Failed change check: same as last analyzed block')
      return false
    }
    
    lastAnalyzedHash.value = blockHash
    console.log('✅ Code block passed all checks!')
    return true
  }
  
  const hashCode = (str: any) => {
    let hash = 0
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i)
      hash = ((hash << 5) - hash) + char
      hash = hash & hash // Convert to 32-bit integer
    }
    return hash
  }

  const handleKeyDown = (event: any) => {
    if (!view.value) return
    
    const editor = view.value
    const cursor = editor.state.selection.main.head
    const cursorPos = editor.state.doc.lineAt(cursor)
    
    if (event.key === 'Enter') {
      consecutiveEnters.value++
      console.log('🔄 Enter pressed, consecutive count:', consecutiveEnters.value)
      
      // Check for double Enter trigger
      if (consecutiveEnters.value >= ENTER_THRESHOLD) {
        console.log('🚀 Double Enter detected - triggering immediate analysis')
        consecutiveEnters.value = 0
        triggerImmediateAnalysis(editor, { line: cursorPos.number - 1, ch: cursor - cursorPos.from })
        return
      }
    } else {
      // Reset consecutive enters on any other key
      if (consecutiveEnters.value > 0) {
        console.log('🔄 Non-Enter key pressed, resetting consecutive count')
        consecutiveEnters.value = 0
      }
    }
  }
  
  const triggerImmediateAnalysis = (editor: any, cursor: any) => {
    console.log('⚡ Immediate analysis triggered')
    
    // Simple race condition prevention: Don't send if panel is already visible
    if (showCodeAnalysis.value) {
      console.log('⚠️ Analysis panel already visible, skipping duplicate request')
      return
    }
    
    // Clear any existing timer to prevent duplicate analysis
    if (userTypingTimer.value) {
      console.log('🔄 Clearing existing timer to prevent race condition')
      clearTimeout(userTypingTimer.value)
      userTypingTimer.value = null
    }
    
    // For immediate triggers (double Enter, outdent), we want to analyze the 
    // most recently completed code block, not necessarily the current cursor position
    const adjustedCursor = findPreviousCodeBlock(editor, cursor)
    
    // Trigger analysis immediately
    onUserStoppedTyping(editor, adjustedCursor)
  }
  
  const findPreviousCodeBlock = (editor: any, cursor: any) => {
    console.log('🔍 Finding previous code block from cursor position:', cursor)
    
    const doc = editor.state.doc
    const currentLine = cursor.line
    
    // Look backwards from current position to find the last non-empty line
    for (let i = currentLine; i >= 0; i--) {
      const lineText = doc.line(i + 1).text
      
      // Skip empty lines and lines with only whitespace
      if (lineText.trim() === '') continue
      
      // Found a non-empty line - this is likely part of the previous code block
      console.log('🎯 Found previous code at line:', i + 1, 'text:', lineText)
      return { line: i, ch: lineText.length }
    }
    
    // If no previous code found, use original cursor position
    console.log('❌ No previous code found, using original cursor position')
    return cursor
  }
  
  const onCursorActivity = (editor: any) => {
    console.log('🔍 onCursorActivity triggered')
    
    // Check if code analysis is disabled
    if (!codeAnalysisSettings.value.enabled) {
      console.log('🚫 Code analysis is disabled')
      return
    }
    
    const cursor = editor.state.selection.main.head
    const cursorPos = editor.state.doc.lineAt(cursor)
    
    lastTypingTime.value = Date.now()
    
    // Simple race condition prevention: Don't set timer if panel is already visible
    if (showCodeAnalysis.value) {
      console.log('⚠️ Analysis panel already visible, skipping timer setup')
      return
    }
    
    // Clear existing timer
    if (userTypingTimer.value) {
      clearTimeout(userTypingTimer.value)
    }
    
    const delay = codeAnalysisSettings.value.delay * 1000 // Convert to milliseconds
    console.log(`⏱️ Setting ${codeAnalysisSettings.value.delay}-second timer for code analysis`)
    
    // Set new timer - wait for user to stop typing
    userTypingTimer.value = setTimeout(() => {
      console.log('⏰ Timer expired, analyzing code...')
      onUserStoppedTyping(editor, { line: cursorPos.number - 1, ch: cursor - cursorPos.from })
    }, delay)
  }
  
  const onUserStoppedTyping = (editor: any, cursor: any) => {
    console.log('⏹️ User stopped typing, extracting code block...')
    
    // Simple race condition prevention: Don't send if panel is already visible
    if (showCodeAnalysis.value) {
      console.log('⚠️ Analysis panel already visible, skipping duplicate request')
      return
    }
    
    try {
      const codeBlock = extractCurrentCodeBlock(editor, cursor)
      console.log('📝 Extracted code block:', codeBlock)
      
      if (shouldAnalyzeCodeBlock(codeBlock)) {
        console.log('✅ Code block passed significance test')
        // Additional delay to ensure user is really done
        setTimeout(() => {
          console.log('🚀 Scheduling code analysis...')
          scheduleCodeAnalysis(codeBlock)
        }, 200)
      } else {
        console.log('❌ Code block failed significance test')
      }
    } catch (error) {
      console.error('💥 Error in code analysis:', error)
    }
  }
  
  const scheduleCodeAnalysis = (codeBlock: any) => {
    console.log('📅 Scheduling code analysis for:', codeBlock)
    
    // Include problem context in the analysis
    const enhancedCodeBlock = {
      ...codeBlock,
      problemContext: currentProblem.value ? {
        title: currentProblem.value.title,
        description: currentProblem.value.description,
        examples: currentProblem.value.examples,
        constraints: currentProblem.value.constraints,
        difficulty: currentProblem.value.difficulty
      } : null
    }
    
    console.log('🎯 Enhanced code block with problem context:', enhancedCodeBlock)
    
    currentCodeBlock.value = enhancedCodeBlock
    showCodeAnalysis.value = true
    console.log('✅ Code analysis panel should be visible now')
  }

  const onHighlightLine = (lineNumber: any) => {
    // Highlight the problematic line in the editor
    if (view.value) {
      const line = view.value.state.doc.line(lineNumber)
      view.value.dispatch({
        selection: { anchor: line.from, head: line.to },
        scrollIntoView: true
      })
    }
  }
  
  const onApplyFix = (issue: any) => {
    // Apply the suggested fix to the code
    if (view.value && issue.suggestedFix && issue.suggestedFix.code) {
      const line = view.value.state.doc.line(issue.line)
      view.value.dispatch({
        changes: {
          from: line.from,
          to: line.to,
          insert: issue.suggestedFix.code
        }
      })
    }
  }
  
  const onExplainIssue = (issue: any) => {
    // Send explanation request to chat
    socket.emit('message', {
      room: roomId,
      content: `Can you explain why this is an issue: "${issue.title}"? The code is: ${issue.codeSnippet}`,
      userId: currentUserId.value,
      username: auth?.user || 'Guest',
      timestamp: new Date().toISOString()
    })
  }
  
  const onCodeAnalysisDismissed = () => {
    showCodeAnalysis.value = false
    currentCodeBlock.value = null
    console.log('🔄 Analysis panel dismissed')
    
    // Clear visual indicators when dismissed
    if (view.value) {
      console.log('🧹 Clearing visual indicators')
      clearCodeAnalysisLineIndicators(view.value)
    }
  }

  const onIssuesFound = (data: any) => {
    if (!data || typeof data !== 'object') {
      console.warn('⚠️ Invalid data received in onIssuesFound:', data)
      return
    }
    
    const { codeBlock, issues, highestSeverity } = data
    console.log(`🎯 Issues found with severity ${highestSeverity}:`, issues)
    
    // Show visual indicators for the code block that has issues
    if (codeBlock && codeBlock.startLine && codeBlock.endLine && view.value) {
      console.log(`🎨 Showing visual indicators for lines ${codeBlock.startLine}-${codeBlock.endLine} with severity ${highestSeverity}`)
      showCodeAnalysisLineIndicators(view.value, codeBlock.startLine, codeBlock.endLine, highestSeverity)
    }
  }

  // Watch for code changes as a fallback
  watch(code, (newValue, oldValue) => {
    console.log('👀 Code watcher triggered - new length:', newValue.length, 'old length:', oldValue?.length || 0)
    
    // Check if code analysis is disabled
    if (!codeAnalysisSettings.value.enabled) {
      console.log('🚫 Code analysis is disabled')
      return
    }
    
    if (newValue !== oldValue && !isLocalUpdate.value) {
      console.log('🔍 Code changed, starting analysis timer...')
      
      // Clear existing timer
      if (userTypingTimer.value) {
        clearTimeout(userTypingTimer.value)
      }
      
      const delay = codeAnalysisSettings.value.delay * 1000 // Convert to milliseconds
      
      // Set new timer - wait for user to stop typing
      userTypingTimer.value = setTimeout(() => {
        console.log('⏰ Code watcher timer expired, analyzing...')
        
        if (view.value) {
          const cursor = view.value.state.selection.main.head
          const cursorPos = view.value.state.doc.lineAt(cursor)
          onUserStoppedTyping(view.value, { line: cursorPos.number - 1, ch: cursor - cursorPos.from })
        }
      }, delay)
    }
  })

  // Debug function for testing
  const testCodeAnalysis = () => {
    console.log('🧪 Testing code analysis with nested loops...')
    const testBlock = {
      code: `for i in range(n):
    for j in range(m):
        if arr[i] + arr[j] == target:
            return [i, j]`,
      startLine: 1,
      endLine: 4,
      cursorLine: 2,
      language: 'python'
    }
    
    console.log('🔍 Testing shouldAnalyzeCodeBlock...')
    const shouldAnalyze = shouldAnalyzeCodeBlock(testBlock)
    console.log('📊 Should analyze?', shouldAnalyze)
    
    if (shouldAnalyze) {
      console.log('✅ Calling scheduleCodeAnalysis...')
      scheduleCodeAnalysis(testBlock)
    }
  }

  // Debug function for testing current code
  const debugCurrentCode = () => {
    console.log('🔍 Debugging current code...')
    console.log('📝 Current code:', code.value)
    console.log('📏 Code length:', code.value.length)
    
    if (view.value) {
      const cursor = view.value.state.selection.main.head
      const cursorPos = view.value.state.doc.lineAt(cursor)
      console.log('📍 Cursor position:', { line: cursorPos.number - 1, ch: cursor - cursorPos.from })
      
      const codeBlock = extractCurrentCodeBlock(view.value, { line: cursorPos.number - 1, ch: cursor - cursorPos.from })
      console.log('🧱 Extracted code block:', codeBlock)
      
      const shouldAnalyze = shouldAnalyzeCodeBlock(codeBlock)
      console.log('🤔 Should analyze?', shouldAnalyze)
      
      if (shouldAnalyze) {
        scheduleCodeAnalysis(codeBlock)
      } else {
        console.log('❌ Code block does not meet analysis criteria')
      }
    } else {
      console.log('❌ No editor view available')
    }
  }

  return {
    // State
    showCodeAnalysis,
    currentCodeBlock,
    consecutiveEnters,
    
    // Methods
    handleKeyDown,
    onCursorActivity,
    onHighlightLine,
    onApplyFix,
    onExplainIssue,
    onCodeAnalysisDismissed,
    onIssuesFound,
    
    // Debug methods
    testCodeAnalysis,
    debugCurrentCode
  }
}
