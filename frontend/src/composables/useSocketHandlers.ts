import { ref, watch } from 'vue'
import { debounce } from 'lodash'

export function useSocketHandlers(socket: any, roomId: any, auth: any, code: any, selectedLanguage: any, currentUserId: any, view: any, lastReceivedContent: any, isLocalUpdate: any, isReadOnly: any, setRemoteCursor: any, clearRemoteCursor: any, generateUserColor: any, showCodeAnalysisLineIndicators: any, showCodeAnalysis: any, currentCodeBlock: any, saveRoomState?: (code: string, language: string) => void) {
  
  const handleRemoteCodeExecution = (data: any) => {
    console.log('📡 Handling remote code execution:', data)
    
    // Show a toast notification
    showExecutionNotification(data)
  }

  const handleRemoteCodeAnalysis = (data: any) => {
    console.log('📊 Received code analysis result from backend:', data)
    
    if (view.value && data.codeBlock && showCodeAnalysisLineIndicators) {
      console.log('📊 Displaying code analysis indicators for all users')
      console.log('📊 Code block:', data.codeBlock)
      console.log('📊 Issues found:', data.issues?.length || 0)
      console.log('📊 Severity:', data.highestSeverity)
      
      try {
        // Show visual indicators for the analyzed code block
        if (data.codeBlock.startLine && data.codeBlock.endLine) {
          showCodeAnalysisLineIndicators(
            view.value, 
            data.codeBlock.startLine, 
            data.codeBlock.endLine, 
            data.highestSeverity || 'medium'
          )
          console.log('✅ Successfully displayed code analysis indicators')
        }
        
        // Set the code block data and let the CodeIssuePanel watcher handle display
        if (currentCodeBlock) {
          console.log('📋 Setting code analysis data for panel')
          currentCodeBlock.value = {
            ...data.codeBlock,
            issues: data.issues,
            highestSeverity: data.highestSeverity,
            isRemoteAnalysis: true,
            remoteUserId: data.userId
          }
          
          // Only set visibility if there are issues to show
          if (showCodeAnalysis) {
            if (data.issues && data.issues.length > 0) {
              console.log('📋 Showing code analysis panel - issues found')
              showCodeAnalysis.value = true
            } else {
              console.log('✅ No issues found - hiding analysis panel')
              showCodeAnalysis.value = false
            }
          }
        }
      } catch (error) {
        console.error('❌ Error displaying code analysis:', error)
      }
    } else {
      console.log('📊 Cannot display code analysis - missing view, codeBlock, or functions')
    }
  }

  const showExecutionNotification = (data) => {
    // Create a temporary notification
    const notification = {
      id: 'exec_notif_' + Date.now(),
      type: 'execution',
      message: `Code executed by another user`,
      details: {
        language: data.language,
        hasOutput: !!(data.result.output),
        hasError: !!(data.result.error),
        executionTime: data.result.executionTime || 'unknown'
      },
      timestamp: Date.now()
    }

    // You can add this to a notifications array if you have one
    // For now, just log it
    console.log('📊 Execution notification:', notification)
  }

  const debouncedBroadcast = debounce((newValue) => {
    if (!isReadOnly.value) {
      socket.emit('update', { 
        room: roomId, 
        delta: newValue,
        sourceId: socket.id 
      })
    }
  }, 200)

  watch(() => code.value, (newValue) => {
    if (!isLocalUpdate.value && !isReadOnly.value) {
      debouncedBroadcast(newValue)
    }
    isLocalUpdate.value = false
  })

  // Handle remote selection updates
  const handleRemoteSelection = (data) => {
    console.log('handleRemoteSelection called with:', data)
    if (data.userId !== socket.id && view.value) {
      console.log('Processing remote selection from different user')
      try {
        // First, always clear any existing selection/cursor for this user
        view.value.dispatch({
          effects: [clearRemoteCursor.of(data.userId)]
        })
        
        // Then, if there's a valid selection, add it
        if (data.from !== data.to && 
            typeof data.from === 'number' && 
            typeof data.to === 'number' && 
            data.from >= 0 && 
            data.to >= 0 &&
            data.from !== 0 || data.to !== 0) { // Don't show selection if both are 0 (deselected)
          
          console.log('Adding remote selection decoration from', data.from, 'to', data.to)
          const userColor = data.classIndex !== undefined ? 
            { classIndex: data.classIndex } : 
            generateUserColor(data.userId, true) // true = remote, it's other
          
          view.value.dispatch({
            effects: [setRemoteCursor.of({
              userId: data.userId,
              from: data.from,
              to: data.to,
              color: data.color || generateUserColor(data.userId, true).color, // true = remote
              classIndex: userColor.classIndex
            })]
          })
        } else {
          console.log('Clearing remote selection (no valid selection or deselected)')
        }
      } catch (error) {
        console.error('Error handling remote selection:', error)
      }
    } else {
      console.log('Ignoring selection from same user or no view')
    }
  }

  // Handle remote cursor updates with additional state tracking
  let lastCursorData = new Map() // Track last cursor data per user
  
  const handleRemoteCursor = (data) => {
    console.log('Received cursor update:', data)
    if (data.userId !== socket.id && view.value) {
      try {
        // Check if this is actually a different position to avoid unnecessary updates
        const lastData = lastCursorData.get(data.userId)
        if (lastData && lastData.from === data.from && lastData.to === data.to) {
          console.log('Ignoring duplicate cursor update for user', data.userId)
          return
        }
        
        lastCursorData.set(data.userId, { from: data.from, to: data.to })
        
        // Use a small delay to ensure proper sequencing
        setTimeout(() => {
          if (view.value) {
            view.value.dispatch({
              effects: [setRemoteCursor.of({
                userId: data.userId,
                from: data.from,
                to: data.to
              })]
            })
          }
        }, 10)
      } catch (error) {
        console.error('Error handling remote cursor:', error)
      }
    }
  }

  const setupSocketHandlers = () => {
    // Wait for connection before joining room
    socket.on('connect', () => {
      // Update current user ID when socket connects
      currentUserId.value = socket.id
      console.log('Socket connected with ID:', socket.id)
      
      socket.emit('join', { 
        room: roomId, 
        username: auth?.user || 'Guest',
        current_code: code.value,  // Send current code to backend
        current_language: selectedLanguage.value  // Send current language to backend
      }, (response: any) => {
        if (response && response.code) {
          // Only update if the response code is different from what we have
          if (response.code !== code.value) {
            console.log('Received different code from server, updating local state')
            lastReceivedContent.value = response.code
            isLocalUpdate.value = true
            code.value = response.code
            
            // Save server code to localStorage
            if (saveRoomState) {
              saveRoomState(response.code, selectedLanguage.value)
            }
          } else {
            console.log('Server code matches local code, keeping current state')
          }
        }
      })
      
      // Also join personal room for individual AI features (code analysis, etc.)
      const personalRoomId = `${roomId}_personal_${socket.id}`
      console.log('🏠 Joining personal room for individual AI features:', personalRoomId)
      socket.emit('join', { 
        room: personalRoomId, 
        username: auth?.user || 'Guest'
      })
    })

    socket.on('update', ({ delta, sourceId }: any) => {
      if (sourceId !== socket.id) {
        lastReceivedContent.value = delta
        isLocalUpdate.value = true
        code.value = delta
        
        // Save received code changes to localStorage for persistence
        if (saveRoomState) {
          saveRoomState(delta, selectedLanguage.value)
        }
      }
    })

    socket.on('cursor', (data: any) => {
      handleRemoteCursor(data)
    })

    socket.on('selection', (data: any) => {
      handleRemoteSelection(data)
    })
    
    socket.on('user_disconnected', (data: any) => {
      if (view.value) {
        view.value.dispatch({
          effects: [clearRemoteCursor.of(data.userId)]
        })
      }
    })

    socket.on('code_execution_result', (data: any) => {
      console.log('📡 Received code execution from another user:', data)
      handleRemoteCodeExecution(data)
    })

    socket.on('code_analysis_result', (data: any) => {
      console.log('📊 Received code analysis from backend:', data)
      handleRemoteCodeAnalysis(data)
    })

    socket.on('connect_error', (error: any) => {
      console.error('Socket connection error:', error)
    })

    // Handle reconnection - rejoin room with current state
    socket.on('reconnect', () => {
      console.log('Socket reconnected, rejoining room with current state')
      socket.emit('join', { 
        room: roomId, 
        username: auth?.user || 'Guest',
        current_code: code.value,  // Send current code to backend
        current_language: selectedLanguage.value  // Send current language to backend
      }, (response: any) => {
        if (response && response.code) {
          // Only update if the response code is different from what we have
          if (response.code !== code.value) {
            console.log('After reconnection: Received different code from server, updating local state')
            lastReceivedContent.value = response.code
            isLocalUpdate.value = true
            code.value = response.code
            
            // Save reconnected server code to localStorage
            if (saveRoomState) {
              saveRoomState(response.code, selectedLanguage.value)
            }
          } else {
            console.log('After reconnection: Server code matches local code, keeping current state')
          }
        }
      })
      
      // Also rejoin personal room for individual AI features
      const personalRoomId = `${roomId}_personal_${socket.id}`
      console.log('🏠 Rejoining personal room for individual AI features:', personalRoomId)
      socket.emit('join', { 
        room: personalRoomId, 
        username: auth?.user || 'Guest'
      })
    })
  }

  const cleanupSocketHandlers = () => {
    socket.off('connect')
    socket.off('update')
    socket.off('cursor')
    socket.off('selection')
    socket.off('user_disconnected')
    socket.off('code_execution_result')
    socket.off('code_analysis_result')
    socket.off('connect_error')
    socket.off('reconnect')
    socket.emit('leave', { room: roomId })
    
    // Also leave personal room
    const personalRoomId = `${roomId}_personal_${socket.id}`
    socket.emit('leave', { room: personalRoomId })
    console.log('🏠 Left personal room:', personalRoomId)
  }

  return {
    setupSocketHandlers,
    cleanupSocketHandlers,
    handleRemoteSelection,
    handleRemoteCursor,
    handleRemoteCodeExecution,
    handleRemoteCodeAnalysis
  }
}
