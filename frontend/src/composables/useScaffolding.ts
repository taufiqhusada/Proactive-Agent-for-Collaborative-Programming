import { ref, watch } from 'vue'

export function useScaffolding(code: any, selectedLanguage: any, socket: any, roomId: any, isLocalUpdate: any, isReadOnly: any, view: any) {
  // Scaffolding notification state
  const showScaffoldingNotification = ref(false)
  const scaffoldingNotificationText = ref('')
  
  const scaffoldingTimer = ref<any>(null)
  const processedComments = ref(new Set()) // Track already processed comments
  const lastProcessedComment = ref('') // Track the last comment we processed
  const activeScaffoldingRequests = ref(new Set()) // Track ongoing scaffolding requests across users
  const scaffoldingLocks = ref(new Map()) // Track who is processing which comment

  const detectScaffoldingTrigger = (newCode: any, oldCode: any) => {
    const newLines = newCode.split('\n')
    const oldLines = oldCode.split('\n')
    
    // Find the line that was just modified
    let modifiedLine = -1
    
    if (newLines.length > oldLines.length) {
      // New line added
      modifiedLine = oldLines.length
    } else {
      // Existing line modified
      for (let i = 0; i < Math.min(newLines.length, oldLines.length); i++) {
        if (newLines[i] !== oldLines[i]) {
          modifiedLine = i
          break
        }
      }
    }
    
    if (modifiedLine >= 0 && modifiedLine < newLines.length) {
      const line = newLines[modifiedLine].trim()
      
      // Check for scaffolding trigger - only ## comments (double comment syntax)
      const scaffoldingPrefixes = {
        'python': '##',           // Python: ##
        'javascript': '// //',    // JavaScript: // //  
        'java': '// //',          // Java: // //
        'cpp': '// //',           // C++: // //
        'typescript': '// //'     // TypeScript: // //
      }
      
      const scaffoldingPrefix = scaffoldingPrefixes[selectedLanguage.value as keyof typeof scaffoldingPrefixes] || '##'
      
      // Only trigger scaffolding for double comment syntax
      if (line.startsWith(scaffoldingPrefix) && line.length > scaffoldingPrefix.length + 1) {
        console.log('🏗️ Double comment detected for scaffolding:', line)
        // Create a unique identifier for this comment (line content + position)
        const commentId = `${modifiedLine}:${line}`
        
        // Check if we already processed this exact comment
        if (processedComments.value.has(commentId) || lastProcessedComment.value === commentId) {
          console.log('🚫 Skipping duplicate scaffolding for:', line)
          return
        }
        
        // Check if another user is already processing this comment
        if (activeScaffoldingRequests.value.has(commentId)) {
          console.log('🚫 Another user is already processing scaffolding for:', line)
          return
        }
        
        console.log('🏗️ Double comment detected, starting 2s timer for scaffolding:', line)
        
        // Clear existing timer
        if (scaffoldingTimer.value) {
          clearTimeout(scaffoldingTimer.value)
        }
        
        // Start 2 second timer
        scaffoldingTimer.value = setTimeout(() => {
          console.log('⏰ 2s timer expired, attempting to claim scaffolding lock...')
          attemptScaffoldingLock(newCode, modifiedLine, commentId)
        }, 2000)
      }
    }
  }
  
  const attemptScaffoldingLock = (code: any, cursorLine: any, commentId: any) => {
    // Try to claim the lock by broadcasting to other users
    socket.emit('scaffolding-lock-request', {
      room: roomId,
      userId: socket.id,
      commentId: commentId,
      timestamp: Date.now()
    })
    
    // Wait a short time to see if anyone else is already processing
    setTimeout(() => {
      // Check if we got the lock (no one else claimed it first)
      if (!activeScaffoldingRequests.value.has(commentId) || 
          scaffoldingLocks.value.get(commentId) === socket.id) {
        
        console.log('🔒 Acquired scaffolding lock for:', commentId)
        activeScaffoldingRequests.value.add(commentId)
        scaffoldingLocks.value.set(commentId, socket.id)
        
        // Broadcast that we're processing this
        socket.emit('scaffolding-lock-acquired', {
          room: roomId,
          userId: socket.id,
          commentId: commentId
        })
        
        requestScaffolding(code, cursorLine, commentId)
      } else {
        console.log('🚫 Failed to acquire scaffolding lock, another user got it first')
      }
    }, 100) // Small delay to allow race condition resolution
  }
  
  const requestScaffolding = async (code: any, cursorLine: any, commentId: any) => {
    try {
      console.log('🔮 Requesting LLM scaffolding for line:', cursorLine)
      
      const response = await fetch('/api/generate-scaffolding', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          code: code,
          language: selectedLanguage.value,
          cursorLine: cursorLine,
          roomId: roomId?.value || null // Include room ID for AI mode checking
        })
      })
      
      const result = await response.json()
      
      if (result.isLocked) {
        console.log('🚫 Backend says scaffolding is locked by another user:', result.message)
        // Another user is already processing this, mark as processed to avoid retries
        processedComments.value.add(commentId)
        return
      }
      
      if (result.hasScaffolding) {
        console.log('✅ LLM generated scaffolding:', result)
        
        // Mark this comment as processed
        processedComments.value.add(commentId)
        lastProcessedComment.value = commentId
        
        showScaffoldingSuggestion(result, cursorLine)
        
        // Broadcast scaffolding completion to other users
        socket.emit('scaffolding-completed', {
          room: roomId,
          userId: socket.id,
          commentId: commentId,
          scaffoldingCode: result.scaffoldingCode,
          cursorLine: cursorLine
        })
      } else {
        console.log('ℹ️ LLM said no scaffolding needed:', result.message)
      }
      
      // Release the lock
      activeScaffoldingRequests.value.delete(commentId)
      scaffoldingLocks.value.delete(commentId)
      
      socket.emit('scaffolding-lock-released', {
        room: roomId,
        userId: socket.id,
        commentId: commentId
      })
      
    } catch (error) {
      console.error('❌ Error requesting scaffolding:', error)
      
      // Release the lock on error
      activeScaffoldingRequests.value.delete(commentId)
      scaffoldingLocks.value.delete(commentId)
      
      socket.emit('scaffolding-lock-released', {
        room: roomId,
        userId: socket.id,
        commentId: commentId
      })
    }
  }
  
  const showScaffoldingSuggestion = (scaffoldingResult: any, lineNumber: any) => {
    // Auto-insert scaffolding code directly below the comment
    if (view.value && scaffoldingResult.scaffoldingCode) {
      const editor = view.value
      const doc = editor.state.doc
      const commentLine = doc.line(lineNumber + 1) // 1-indexed
      
      // Insert scaffolding code after the comment line (not replacing it)
      const insertPosition = commentLine.to
      
      const transaction = editor.state.update({
        changes: {
          from: insertPosition,
          to: insertPosition,
          insert: '\n' + scaffoldingResult.scaffoldingCode
        }
      })
      
      editor.dispatch(transaction)
      
      // Show simple notification
      scaffoldingNotificationText.value = `Added scaffolding: ${scaffoldingResult.originalComment}`
      showScaffoldingNotification.value = true
      
      // Auto-hide notification after 3 seconds
      setTimeout(() => {
        showScaffoldingNotification.value = false
      }, 3000)
      
      console.log('✅ Auto-inserted scaffolding below comment')
    }
  }

  const handleScaffoldingSocketEvents = () => {
    // Scaffolding coordination events
    socket.on('scaffolding-lock-request', (data) => {
      if (data.userId !== socket.id) {
        console.log('📡 Received scaffolding lock request from another user:', data.commentId)
        // Mark as active to prevent our own attempts
        activeScaffoldingRequests.value.add(data.commentId)
        scaffoldingLocks.value.set(data.commentId, data.userId)
      }
    })
    
    socket.on('scaffolding-lock-acquired', (data) => {
      if (data.userId !== socket.id) {
        console.log('📡 Another user acquired scaffolding lock:', data.commentId)
        activeScaffoldingRequests.value.add(data.commentId)
        scaffoldingLocks.value.set(data.commentId, data.userId)
      }
    })
    
    socket.on('scaffolding-completed', (data) => {
      if (data.userId !== socket.id) {
        console.log('📡 Scaffolding completed by another user:', data.commentId)
        // Mark as processed to prevent duplicate attempts
        processedComments.value.add(data.commentId)
        lastProcessedComment.value = data.commentId
      }
    })
    
    socket.on('scaffolding-lock-released', (data) => {
      if (data.userId !== socket.id) {
        console.log('📡 Scaffolding lock released by another user:', data.commentId)
        activeScaffoldingRequests.value.delete(data.commentId)
        scaffoldingLocks.value.delete(data.commentId)
      }
    })
  }

  const cleanupScaffoldingSocketEvents = () => {
    socket.off('scaffolding-lock-request')
    socket.off('scaffolding-lock-acquired')
    socket.off('scaffolding-completed')
    socket.off('scaffolding-lock-released')
  }

  // Watch for code changes to detect scaffolding triggers
  watch(() => code.value, (newValue, oldValue) => {
    if (newValue !== oldValue && !isLocalUpdate.value && !isReadOnly.value) {
      // Clean up processed comments that no longer exist in the code
      const currentLines = newValue.split('\n')
      const cleanedProcessedComments = new Set()
      
      processedComments.value.forEach(commentId => {
        const [lineNum, content] = commentId.split(':')
        const currentLineContent = currentLines[parseInt(lineNum)]?.trim()
        
        // Keep the comment in processed list only if it still exists and matches
        if (currentLineContent && commentId.includes(currentLineContent)) {
          cleanedProcessedComments.add(commentId)
        }
      })
      
      processedComments.value = cleanedProcessedComments
      
      // Debounce to avoid too many triggers
      setTimeout(() => {
        detectScaffoldingTrigger(newValue, oldValue || '')
      }, 100)
    }
  })

  return {
    // State
    showScaffoldingNotification,
    scaffoldingNotificationText,
    processedComments,
    activeScaffoldingRequests,
    scaffoldingLocks,
    
    // Methods
    detectScaffoldingTrigger,
    handleScaffoldingSocketEvents,
    cleanupScaffoldingSocketEvents
  }
}
