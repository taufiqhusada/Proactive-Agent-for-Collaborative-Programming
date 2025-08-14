import { ref, computed } from 'vue'
import { StateField, StateEffect, EditorState } from '@codemirror/state'
import { EditorView, Decoration, WidgetType } from '@codemirror/view'

export function useCodeMirrorExtensions(selectedLanguage: any, isReadOnly: any, languages: any) {
  // Effects for managing remote cursors
  const setRemoteCursor = StateEffect.define()
  const clearRemoteCursor = StateEffect.define()
  
  // Effects for managing code analysis line indicators
  const setCodeAnalysisLines = StateEffect.define()
  const clearCodeAnalysisLines = StateEffect.define()

  // Widget for displaying remote cursors
  class RemoteCursorWidget extends WidgetType {
    userId: any
    
    constructor(userId: any) {
      super()
      this.userId = userId
    }
    
    toDOM() {
      const cursor = document.createElement('span')
      cursor.className = `remote-cursor remote-cursor-${this.userId}`
      cursor.style.cssText = `
        position: relative;
        display: inline-block;
        width: 2px;
        height: 1em;
        background: #ef4444;
        border-radius: 1px;
        margin-left: -1px;
        pointer-events: none;
        z-index: 45;
        opacity: 1;
      `
      return cursor
    }

    eq(other: any) {
      return other instanceof RemoteCursorWidget && other.userId === this.userId
    }
  }
  
  // Code Analysis Line Indicator Widget
  class CodeAnalysisLineWidget extends WidgetType {
    severity: any
    
    constructor(severity = 'medium') {
      super()
      this.severity = severity
    }
    
    toDOM() {
      const indicator = document.createElement('div')
      indicator.className = `code-analysis-line-indicator severity-${this.severity}`
      
      // Get color based on severity (matching CodeIssuePanel colors)
      let color = '#ffc107' // medium/yellow
      if (this.severity === 'high') color = '#dc3545' // red
      if (this.severity === 'low') color = '#28a745' // green
      
      indicator.style.cssText = `
        position: absolute;
        left: -6px;
        top: 0;
        width: 4px;
        height: 100%;
        background: ${color};
        border-radius: 2px;
        z-index: 10;
        pointer-events: none;
        opacity: 0.8;
        margin-top: 0;
        box-shadow: 0 0 2px rgba(0,0,0,0.2);
      `
      
      console.log(`🎨 Created code analysis indicator with color ${color} for severity ${this.severity}`)
      return indicator
    }

    eq(other) {
      return other instanceof CodeAnalysisLineWidget && other.severity === this.severity
    }
  }

  // Generate simple color for user - just "me" vs "other"
  const generateUserColor = (userId, isRemote = false) => {
    // If it's a remote selection/cursor, it's always "other"
    // If it's local, it's always "me"
    if (isRemote) {
      return {
        color: '#ef4444',
        classIndex: 'other'
      }
    } else {
      return {
        color: '#4f46e5',
        classIndex: 'me'
      }
    }
  }
  
  // State field to store remote cursor decorations
  const remoteCursorField = StateField.define({
    create() {
      return Decoration.none
    },
    update(decorations, tr) {
      decorations = decorations.map(tr.changes)
      
      for (let effect of tr.effects) {
        if (effect.is(setRemoteCursor)) {
          const { userId, from, to, classIndex } = effect.value
          
          console.log(`Setting cursor for user ${userId}: from ${from} to ${to}`)
          
          // First, completely remove ALL old decorations for this user
          let newDecorations = []
          decorations.between(0, decorations.length, (decorFrom, decorTo, decoration) => {
            const className = decoration.spec.class || ''
            const isWidget = decoration.spec.widget instanceof RemoteCursorWidget
            const widgetUserId = isWidget ? decoration.spec.widget.userId : null
            
            // Clear ANY remote selection and ANY cursor widget for this user
            const isRemoteSelection = className.includes('remote-selection-')
            const isThisUserCursor = isWidget && widgetUserId === userId
            
            if (!isRemoteSelection && !isThisUserCursor) {
              newDecorations.push(decoration.range(decorFrom, decorTo))
            } else {
              console.log(`Removing old decoration for user ${userId}: ${className || 'cursor widget'}`)
            }
          })
          
          // Create fresh decoration set without old user decorations
          decorations = Decoration.set(newDecorations)
          
          // Ensure positions are valid
          const validFrom = Math.max(0, Math.min(from, tr.newDoc.length))
          const validTo = Math.max(0, Math.min(to, tr.newDoc.length))
          
          // If there's a selection (from !== to), show selection highlight ONLY
          if (validFrom !== validTo) {
            const selectionFrom = Math.min(validFrom, validTo)
            const selectionTo = Math.max(validFrom, validTo)
            
            console.log(`Adding selection for user ${userId}: ${selectionFrom} to ${selectionTo}`)
            
            const userColorInfo = classIndex !== undefined ? 
              { classIndex } : 
              generateUserColor(userId, true) // true = remote user
            
            const selectionDecoration = Decoration.mark({
              class: `remote-selection-${userColorInfo.classIndex}`,
            }).range(selectionFrom, selectionTo)
            
            decorations = decorations.update({
              add: [selectionDecoration]
            })
          } else {
            // If no selection, show cursor at the position ONLY
            console.log(`Adding cursor for user ${userId} at position ${validTo}`)
            
            const cursorDecoration = Decoration.widget({
              widget: new RemoteCursorWidget(userId),
              side: 1
            }).range(validTo)
            
            decorations = decorations.update({
              add: [cursorDecoration]
            })
          }
        } else if (effect.is(clearRemoteCursor)) {
          const userId = effect.value
          console.log(`Clearing all decorations for user ${userId}`)
          
          decorations = decorations.update({
            filter: (from, to, decoration) => {
              const className = decoration.spec.class || ''
              const isWidget = decoration.spec.widget instanceof RemoteCursorWidget
              const widgetUserId = isWidget ? decoration.spec.widget.userId : null
              
              // Clear ANY selection that contains "remote-selection-" and ANY cursor widget for this user
              const isRemoteSelection = className.includes('remote-selection-')
              const isThisUserCursor = isWidget && widgetUserId === userId
              
              // Keep decorations that are NOT remote selections AND not this user's cursor
              const shouldKeep = !isRemoteSelection && !isThisUserCursor
              
              if (!shouldKeep) {
                console.log(`Removing decoration for user ${userId}: ${className || 'cursor widget'}`)
              }
              
              return shouldKeep
            }
          })
        }
      }
      
      return decorations
    },
    provide: f => EditorView.decorations.from(f)
  })

  // State field to store code analysis line indicators
  const codeAnalysisField = StateField.define({
    create() {
      return Decoration.none
    },
    update(decorations, tr) {
      decorations = decorations.map(tr.changes)
      
      for (let effect of tr.effects) {
        if (effect.is(setCodeAnalysisLines)) {
          const { startLine, endLine, severity = 'medium' } = effect.value || {}
          
          // Validate input parameters
          if (!startLine || !endLine || typeof startLine !== 'number' || typeof endLine !== 'number') {
            console.warn('⚠️ Invalid line numbers in setCodeAnalysisLines effect:', effect.value)
            continue
          }
          
          console.log(`Setting code analysis indicators for lines ${startLine}-${endLine} with severity ${severity}`)
          
          // Clear existing code analysis decorations
          try {
            decorations = decorations.update({
              filter: (from, to, decoration) => {
                if (!decoration || !decoration.spec) return true
                // Filter out both widget and line decorations for code analysis
                const isCodeAnalysisWidget = decoration.spec.widget instanceof CodeAnalysisLineWidget
                const isCodeAnalysisLine = decoration.spec.class && decoration.spec.class.includes('code-analysis-line-mark')
                return !isCodeAnalysisWidget && !isCodeAnalysisLine
              }
            })
          } catch (error) {
            console.error('❌ Error clearing existing decorations:', error)
          }
          
          // Add new line indicators
          const newDecorations = []
          for (let lineNum = startLine; lineNum <= endLine; lineNum++) {
            try {
              if (!tr.state || !tr.state.doc) {
                console.warn('⚠️ Invalid transaction state')
                continue
              }
              
              const line = tr.state.doc.line(lineNum)
              if (!line || line.from === undefined) {
                console.warn(`⚠️ Could not get line ${lineNum}`)
                continue
              }
              
              // Try both approaches for better visibility
              
              // 1. Line decoration approach (applies class to entire line)
              const lineMarkDecoration = Decoration.line({
                class: `code-analysis-line-mark severity-${severity}`
              }).range(line.from)
              
              // 2. Widget decoration approach (creates visible indicator)
              const widgetDecoration = Decoration.widget({
                widget: new CodeAnalysisLineWidget(severity),
                side: -1
              }).range(line.from)
              
              newDecorations.push(lineMarkDecoration)
              newDecorations.push(widgetDecoration) // Add the widget decoration too!
              
              console.log(`🎯 Added line decoration for line ${lineNum} at position ${line.from}`)
            } catch (e) {
              console.warn(`Could not create decoration for line ${lineNum}:`, e)
            }
          }
          
          if (newDecorations.length > 0) {
            try {
              decorations = decorations.update({
                add: newDecorations
              })
              console.log(`✅ Successfully added ${newDecorations.length} line decorations`)
            } catch (error) {
              console.error('❌ Error adding new decorations:', error)
            }
          }
        } else if (effect.is(clearCodeAnalysisLines)) {
          console.log('Clearing all code analysis line indicators')
          try {
            decorations = decorations.update({
              filter: (from, to, decoration) => {
                if (!decoration || !decoration.spec) return true
                // Filter out both widget and line decorations for code analysis
                const isCodeAnalysisWidget = decoration.spec.widget instanceof CodeAnalysisLineWidget
                const isCodeAnalysisLine = decoration.spec.class && decoration.spec.class.includes('code-analysis-line-mark')
                return !isCodeAnalysisWidget && !isCodeAnalysisLine
              }
            })
          } catch (error) {
            console.error('❌ Error clearing decorations:', error)
          }
        }
      }
      
      return decorations
    },
    provide: f => EditorView.decorations.from(f)
  })

  // Extension to detect selection and cursor changes
  const selectionUpdateExtension = EditorView.updateListener.of((update) => {
    if ((update.selectionSet || update.focusChanged) && !isReadOnly.value) {
      // Only broadcast if this is a real user selection change, not a programmatic update
      if (!update.transactions.some(tr => tr.effects.some(e => e.is(setRemoteCursor)))) {
        const selection = update.state.selection.main
        if (selection.from !== selection.to) {
          // Broadcast selection when text is selected
          window.broadcastSelection && window.broadcastSelection()
        } else {
          // Broadcast cursor when just cursor position changes
          window.broadcastCursor && window.broadcastCursor()
        }
      }
    }
  })

  // Helper function to get indentation level
  const getIndentLevel = (lineText: string) => {
    const match = lineText.match(/^(\s*)/)
    return match ? match[1].length : 0
  }

  // Helper function to detect if a line starts a code block
  const isBlockStart = (lineText: string) => {
    const trimmed = lineText.trim()
    if (trimmed === '') return false
    
    const patterns = [
      // Function definitions
      /^\s*(def|function)\s+\w+.*:/,
      /^\s*(async\s+)?(def|function)\s+\w+.*:/,
      // Class definitions
      /^\s*class\s+\w+.*:/,
      // Control structures
      /^\s*(if|elif|else|for|while|try|except|finally|with)\s*.*:/,
      // Method definitions in classes
      /^\s*(public|private|protected|static)?\s*(def|function)\s+\w+.*:/,
      // JavaScript/Java function patterns
      /^\s*(public|private|protected|static)?\s*\w+\s*=\s*function.*\{/,
      /^\s*function\s+\w+.*\{/,
      // Simple assignment that could start a logical block
      /^\s*\w+\s*=\s*\[/,  // Array assignment
      /^\s*\w+\s*=\s*\{/,  // Dict/Object assignment
      // Common algorithmic patterns
      /^\s*for\s+\w+\s+in\s+range\s*\(/,
      /^\s*for\s+\w+\s+in\s+\w+/,
      /^\s*while\s+\w+/,
      /^\s*if\s+\w+/,
    ]
    
    return patterns.some(pattern => pattern.test(lineText))
  }

  // Helper function to detect if a position is inside a function or code block
  const isInsideFunction = (view: any, pos: number) => {
    const doc = view.state.doc
    const clickLine = doc.lineAt(pos)
    
    // Look for the nearest block start above the current position
    for (let i = clickLine.number; i > 0 && i > clickLine.number - 50; i--) {
      const line = doc.line(i)
      const lineText = line.text
      
      // Skip empty lines
      if (lineText.trim() === '') continue
      
      // If we find a block start, check if we're likely inside it
      if (isBlockStart(lineText)) {
        const blockIndent = getIndentLevel(lineText)
        
        // Check if there's content after the block start with proper indentation
        for (let j = i + 1; j <= Math.min(doc.lines, i + 20); j++) {
          const checkLine = doc.line(j)
          const checkText = checkLine.text
          
          // Skip empty lines
          if (checkText.trim() === '') continue
          
          const checkIndent = getIndentLevel(checkText)
          
          // If we find indented content, this is likely a real block
          if (checkIndent > blockIndent) {
            // Check if the clicked line is within this block's scope
            if (clickLine.number >= i && clickLine.number <= j + 10) {
              return true
            }
          }
          
          // If we hit another block at same or lower indentation, stop
          if (checkIndent <= blockIndent && isBlockStart(checkText)) {
            break
          }
        }
      }
    }
    
    // Also check if we're on a line that has some code content (not just empty)
    const currentText = clickLine.text.trim()
    if (currentText.length > 3 && !currentText.startsWith('//') && !currentText.startsWith('#')) {
      return true
    }
    
    return false
  }

  // Helper function to extract code block around cursor position
  const extractCodeBlockAtPosition = (view: any, pos: number) => {
    const doc = view.state.doc
    const clickLine = doc.lineAt(pos)
    
    let startLine = clickLine.number
    let endLine = clickLine.number
    let blockIndent = null
    
    // Find the start of the logical block by looking backwards
    for (let i = clickLine.number; i > 0; i--) {
      const line = doc.line(i)
      const lineText = line.text
      
      // Skip empty lines when looking for block start
      if (lineText.trim() === '') continue
      
      const indent = getIndentLevel(lineText)
      
      // If this is a block start and we haven't found one yet
      if (isBlockStart(lineText) && blockIndent === null) {
        startLine = i
        blockIndent = indent
        break
      }
      
      // If we have a block indent and this line has equal or less indentation
      // and it's a block start, we found our boundary
      if (blockIndent !== null && indent <= blockIndent && isBlockStart(lineText)) {
        startLine = i
        blockIndent = indent
      }
      
      // If we go too far back or hit a line with very low indentation, stop
      if (i < clickLine.number - 30 || (indent === 0 && lineText.trim() !== '' && !isBlockStart(lineText))) {
        break
      }
    }
    
    // If we didn't find a clear block start, use a reasonable starting point
    if (blockIndent === null) {
      // Start from a few lines above or beginning of meaningful code
      for (let i = Math.max(1, clickLine.number - 10); i <= clickLine.number; i++) {
        const line = doc.line(i)
        if (line.text.trim() !== '') {
          startLine = i
          blockIndent = getIndentLevel(line.text)
          break
        }
      }
    }
    
    // Find the end of the logical block by looking forwards
    for (let i = startLine; i <= doc.lines && i < startLine + 50; i++) {
      const line = doc.line(i)
      const lineText = line.text
      const indent = getIndentLevel(lineText)
      
      // Skip empty lines - they don't determine block boundaries
      if (lineText.trim() === '') {
        endLine = i
        continue
      }
      
      // If we hit another block at the same or lower indentation level, stop
      if (i > startLine && blockIndent !== null && indent <= blockIndent && isBlockStart(lineText)) {
        endLine = i - 1
        break
      }
      
      // If we hit a line with much lower indentation (like top-level code), stop
      if (i > startLine && blockIndent !== null && indent < blockIndent && lineText.trim() !== '') {
        endLine = i - 1
        break
      }
      
      endLine = i
    }
    
    // Ensure we have a reasonable block size
    if (endLine - startLine < 1) {
      endLine = Math.min(doc.lines, startLine + 5)
    }
    
    // Extract the code, including empty lines to preserve structure
    const codeLines = []
    for (let i = startLine; i <= endLine; i++) {
      codeLines.push(doc.line(i).text)
    }
    
    // Clean up trailing empty lines
    while (codeLines.length > 0 && codeLines[codeLines.length - 1].trim() === '') {
      codeLines.pop()
    }
    
    console.log(`🔍 Extracted code block from lines ${startLine}-${endLine}:`)
    console.log(codeLines.join('\n'))
    
    return {
      code: codeLines.join('\n'),
      startLine: startLine,
      endLine: endLine,
      cursorLine: clickLine.number,
      language: selectedLanguage.value
    }
  }

  // Click handler extension for code analysis popup
  const clickHandlerExtension = EditorView.domEventHandlers({
    contextmenu(event, view) {
      // Handle right-click
      if (isReadOnly.value) return false
      
      const pos = view.posAtCoords({ x: event.clientX, y: event.clientY })
      if (pos === null) return false
      
      // Check if we're inside a function or code block
      if (isInsideFunction(view, pos)) {
        event.preventDefault()
        
        // Get the code block at this position
        const codeBlock = extractCodeBlockAtPosition(view, pos)
        
        // Show the popup at cursor position
        if ((window as any).showCodeAnalysisPopup) {
          (window as any).showCodeAnalysisPopup(
            { x: event.clientX, y: event.clientY },
            codeBlock
          )
        }
        
        console.log('🖱️ Right-click in function detected, showing analysis popup')
        return true
      }
      
      return false
    },
    
    click(event, view) {
      // Handle left-click with modifier keys (Ctrl/Cmd + Click)
      if (!event.ctrlKey && !event.metaKey) return false
      if (isReadOnly.value) return false
      
      const pos = view.posAtCoords({ x: event.clientX, y: event.clientY })
      if (pos === null) return false
      
      // Check if we're inside a function or code block
      if (isInsideFunction(view, pos)) {
        event.preventDefault()
        
        // Get the code block at this position
        const codeBlock = extractCodeBlockAtPosition(view, pos)
        
        // Show the popup at cursor position
        if ((window as any).showCodeAnalysisPopup) {
          (window as any).showCodeAnalysisPopup(
            { x: event.clientX, y: event.clientY },
            codeBlock
          )
        }
        
        console.log('🖱️ Ctrl+Click in function detected, showing analysis popup')
        return true
      }
      
      return false
    }
  })

  // Computed property for extensions that includes readonly state, remote cursors, and code analysis indicators
  const computedExtensions = computed(() => {
    const langExtension = languages[selectedLanguage.value]
    const baseExtensions = [langExtension, remoteCursorField, codeAnalysisField, selectionUpdateExtension, clickHandlerExtension]
    if (isReadOnly.value) {
      baseExtensions.push(EditorState.readOnly.of(true))
      baseExtensions.push(EditorView.editable.of(false))
    }
    return baseExtensions
  })

  // Helper functions for managing code analysis line indicators
  const showCodeAnalysisLineIndicators = (view, startLine, endLine, severity = 'medium') => {
    if (!view || !view.state || !view.dispatch) {
      console.warn('⚠️ Editor view not ready for line indicators')
      return
    }
    
    // Validate line numbers
    if (!startLine || !endLine || startLine < 1 || endLine < startLine) {
      console.warn('⚠️ Invalid line numbers:', { startLine, endLine })
      return
    }
    
    console.log(`🟡 Showing code analysis line indicators for lines ${startLine}-${endLine} with severity ${severity}`)
    
    try {
      view.dispatch({
        effects: setCodeAnalysisLines.of({
          startLine,
          endLine,
          severity
        })
      })
    } catch (error) {
      console.error('❌ Error showing line indicators:', error)
    }
  }
  
  const clearCodeAnalysisLineIndicators = (view) => {
    if (!view || !view.dispatch) {
      console.warn('⚠️ Editor view not ready for clearing indicators')
      return
    }
    
    console.log('🔄 Clearing code analysis line indicators')
    
    try {
      view.dispatch({
        effects: clearCodeAnalysisLines.of()
      })
    } catch (error) {
      console.error('❌ Error clearing line indicators:', error)
    }
  }
  
  const updateCodeAnalysisLineIndicators = (view, startLine, endLine, severity = 'medium') => {
    // Clear existing indicators and show new ones
    clearCodeAnalysisLineIndicators(view)
    // Add a small delay to ensure clearing completes
    setTimeout(() => {
      showCodeAnalysisLineIndicators(view, startLine, endLine, severity)
    }, 10)
  }

  return {
    // Effects
    setRemoteCursor,
    clearRemoteCursor,
    setCodeAnalysisLines,
    clearCodeAnalysisLines,
    
    // State fields
    remoteCursorField,
    codeAnalysisField,
    
    // Extensions
    selectionUpdateExtension,
    computedExtensions,
    
    // Utilities
    generateUserColor,
    showCodeAnalysisLineIndicators,
    clearCodeAnalysisLineIndicators,
    updateCodeAnalysisLineIndicators,
    
    // Widgets
    RemoteCursorWidget,
    CodeAnalysisLineWidget
  }
}
