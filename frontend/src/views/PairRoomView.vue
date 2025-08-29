<template>
    <div class="editor-container">
        <div class="editor-header">
            <div class="header-content">
                <h1 class="room-title">
                  Code and Learn 
                  <span class="highlight-together">Together</span>
                </h1>
                
                <p class="powered-by">Powered by human + human + AI</p>
               
                <!-- <p class="room-id">Room: {{ roomId }}</p> -->
            </div>
            <div class="controls">
                <div class="language-selector">
                    <label for="languageSelect">Language:</label>
                    <select id="languageSelect" v-model="selectedLanguage" @change="updateLanguage">
                        <option value="python">🐍 Python</option>
                        <option value="java">☕ Java</option>
                        <option value="cpp">⚡ C++</option>
                    </select>
                </div>
                <div class="ai-mode-control">
                    <AIModeToggle 
                        :room-id="roomId"
                        :user-id="currentUserId"
                        :socket="socket"
                        :session-started="chatSessionStarted"
                        @mode-changed="handleAIModeChanged"
                    />
                </div>
                <!-- <div class="mode-toggle">
                    <label class="switch">
                        <input type="checkbox" v-model="isReadOnly" id="readOnlyMode">
                        <span class="slider"></span>
                    </label>
                    <label for="readOnlyMode" class="mode-label">Read-only Mode</label>
                </div> -->
            </div>
        </div>

        <div class="main-content">
            <!-- Left Panel: Problem Description -->
            <div class="left-panel">
                <ProblemDescription 
                    :selected-problem="selectedProblem" 
                    :language="selectedLanguage"
                    @problem-changed="onProblemChanged" 
                    @boilerplate-changed="onBoilerplateChanged" 
                />
            </div>

            <!-- Center Panel: Code Editor -->
            <div class="center-panel">
                <div class="editor-wrapper">
                    <codemirror 
                        v-model="code" 
                        :autofocus="!isReadOnly"
                        :indent-with-tab="true"
                        :tab-size="2" 
                        :extensions="computedExtensions"
                        @ready="handleReady" 
                        @change="handleCodeChange"
                        class="code-editor" />
                </div>
                
                <!-- Code Runner -->
                <CodeRunner 
                    :code="code"
                    :language="selectedLanguage"
                    :room-id="roomId"
                    :socket="socket"
                    :current-user-id="currentUserId"
                    :ai-mode="currentAIMode"
                    @chat-message="handleCodeRunnerChatMessage"
                    @send-to-personal-ai="handleCodeRunnerPersonalAI"
                />
            </div>

            <!-- Right Panel: Chat -->
            <div class="right-panel">
                <ChatContainer 
                    ref="chatContainer"
                    :socket="socket" 
                    :room-id="roomId" 
                    :current-user-id="currentUserId"
                    :username="auth?.user || 'Guest'"
                    :reflection-session-id="reflectionSessionId"
                    :show-reflection-session="showReflectionSession"
                    :current-problem="currentProblem"
                    @reflection-session-started="handleReflectionSessionStarted"
                    @reflection-session-ended="handleReflectionSessionEnded"
                    @start-reflection="startReflectionSession"
                    @stop-reflection="stopReflectionSession"
                    @session-state-changed="handleChatSessionStateChanged" />
            </div>
        </div>
        
        <!-- Code Issue Analysis Panel -->
        <CodeIssuePanel 
            :visible="showCodeAnalysis"
            :code-block="currentCodeBlock"
            :editor-position="{ top: 100, left: 0 }"
            :room-id="roomId"
            :socket="socket"
            :current-user-id="currentUserId"
            @highlight-line="onHighlightLine"
            @apply-fix="onApplyFix"
            @explain-issue="onExplainIssue"
            @dismissed="onCodeAnalysisDismissed"
            @issues-found="onIssuesFound"
        />
        
        <!-- Simple Scaffolding Notification -->
        <div v-if="showScaffoldingNotification" class="scaffolding-notification">
            <div class="notification-content">
                <span class="notification-icon">🏗️</span>
                <span class="notification-text">{{ scaffoldingNotificationText }}</span>
            </div>
        </div>

        <!-- Code Analysis Popup -->
        <CodeAnalysisPopup 
            :visible="showCodeAnalysisPopup"
            :position="popupPosition"
            :code-block="popupCodeBlock"
            @analyze="handlePopupAnalyze"
            @close="handlePopupClose"
        />

        <!-- TODO Reveal Popup -->
        <TodoRevealPopup 
            :visible="showTodoRevealPopup"
            :position="todoPopupPosition"
            :todo-data="todoData"
            @reveal="handleTodoReveal"
            @analyze="handleTodoAnalyze"
            @close="handleTodoPopupClose"
        />
    </div>
</template>

<script>
import { defineComponent, ref, shallowRef, onMounted, watch, computed } from 'vue'
import { Codemirror } from 'vue-codemirror'
import { python } from '@codemirror/lang-python'
import { java } from '@codemirror/lang-java'
import { cpp } from '@codemirror/lang-cpp'
import { EditorState } from '@codemirror/state'
import { EditorView } from '@codemirror/view'
import { useRoute } from 'vue-router'
import { useSocket } from '@/lib/socket'
import { runCode } from '@/lib/runCode'
import { debounce } from 'lodash'
import { useAuth } from '@/stores/useAuth'
import ProblemDescription from '@/components/ProblemDescription.vue'
import ChatContainer from '@/components/ChatContainer.vue'
import AIModeToggle from '@/components/AIModeToggle.vue'
import CodeIssuePanel from '@/components/CodeIssuePanel.vue'
import CodeRunner from '@/components/CodeRunner.vue'
import CodeAnalysisPopup from '@/components/CodeAnalysisPopup.vue'
import TodoRevealPopup from '@/components/TodoRevealPopup.vue'

// Import composables
import { useCodeAnalysis } from '@/composables/useCodeAnalysis'
import { useScaffolding } from '@/composables/useScaffolding'
import { useReflectionSession } from '@/composables/useReflectionSession'
import { useCodeMirrorExtensions } from '@/composables/useCodeMirrorExtensions'
import { useSocketHandlers } from '@/composables/useSocketHandlers'
import { useRoomPersistence } from '@/composables/useLocalStorage'

// Import styles
export default defineComponent({
    components: {
        Codemirror,
        ProblemDescription,
        ChatContainer,
        AIModeToggle,
        CodeIssuePanel,
        CodeRunner,
        CodeAnalysisPopup,
        TodoRevealPopup,
    },

    setup() {
        const route = useRoute()
        const auth = useAuth()
        const roomId = String(route.params.roomId)
        
        // Import room persistence composable
        const { getPersistedCode, getPersistedLanguage, saveRoomState } = useRoomPersistence(roomId)
        
        // Initialize with persisted state if available
        const code = ref(getPersistedCode())
        const selectedLanguage = ref(getPersistedLanguage())
        
        // Log initialization state
        console.log('📁 Room initialized with:', {
            roomId,
            persistedCode: code.value.substring(0, 50) + '...',
            persistedLanguage: selectedLanguage.value
        })

        const extensions = ref([python()])
        const view = shallowRef()
        const lastReceivedContent = ref('')
        const isReadOnly = ref(false)
        const isLocalUpdate = ref(false)
        const currentUserId = ref('')
        const currentProblem = ref(null)
        const selectedProblem = ref(0)
        const chatSessionStarted = ref(false)
        const currentAIMode = ref('shared') // Track current AI mode
        const { socket, connect } = useSocket()
        
        // Component refs
        const chatContainer = ref(null)
        
        // Code Analysis Popup State
        const showCodeAnalysisPopup = ref(false)
        const popupPosition = ref({ x: 0, y: 0 })
        const popupCodeBlock = ref(null)

        // TODO Reveal Popup State
        const showTodoRevealPopup = ref(false)
        const todoPopupPosition = ref({ x: 0, y: 0 })
        const todoData = ref(null)

        const languages = {
            python: python(),
            java: java(),
            cpp: cpp(),
        }

        const codeMirrorExtensions = useCodeMirrorExtensions(
            selectedLanguage, isReadOnly, languages
        )

        // Initialize composables
        const codeAnalysis = useCodeAnalysis(
            code, selectedLanguage, currentProblem, socket, roomId, 
            currentUserId, auth, view, isLocalUpdate, isReadOnly,
            codeMirrorExtensions.showCodeAnalysisLineIndicators,
            codeMirrorExtensions.clearCodeAnalysisLineIndicators
        )
        
        const scaffolding = useScaffolding(
            code, selectedLanguage, socket, roomId, 
            isLocalUpdate, isReadOnly, view
        )
        
        const reflectionSession = useReflectionSession(socket, roomId)
        
        const socketHandlers = useSocketHandlers(
            socket, roomId, auth, code, selectedLanguage, currentUserId, 
            view, lastReceivedContent, isLocalUpdate, isReadOnly,
            codeMirrorExtensions.setRemoteCursor, codeMirrorExtensions.clearRemoteCursor, 
            codeMirrorExtensions.generateUserColor, codeMirrorExtensions.showCodeAnalysisLineIndicators,
            codeAnalysis.showCodeAnalysis, codeAnalysis.currentCodeBlock, saveRoomState
        )

        const updateLanguage = () => {
            const newExtension = languages[selectedLanguage.value]
            extensions.value = [newExtension, ...(isReadOnly.value ? [EditorState.readOnly.of(true)] : [])]
        }

        const handleReady = (payload) => {
            view.value = payload.view
            
            // Add keyboard event listener for enhanced detection
            const editorDom = view.value.dom
            editorDom.addEventListener('keydown', codeAnalysis.handleKeyDown)
            
            // Add Enter key tracking with proper state management
            let isEnterKeyPressed = false
            let enterPressLineContent = ''
            let enterPressLineNumber = -1
            
            // Listen for keydown to detect Enter key
            editorDom.addEventListener('keydown', (event) => {
                if (event.key === 'Enter' || event.keyCode === 13) {
                    isEnterKeyPressed = true
                    
                    // Capture the current line BEFORE any changes
                    const state = view.value.state
                    const cursor = state.selection.main.head
                    const line = state.doc.lineAt(cursor)
                    const lineNumber = line.number - 1
                    
                    // Store the line content before Enter processing
                    enterPressLineContent = line.text
                    enterPressLineNumber = lineNumber
                    
                    console.log('⌨️ Enter key detected (BEFORE processing):', {
                        lineNumber,
                        originalLine: `"${line.text}"`,
                        trimmedLine: `"${line.text.trim()}"`,
                        hasContent: line.text.trim().length > 0,
                        cursorPosition: cursor
                    })
                    
                    // Use a small timeout to capture after the Enter is processed
                    setTimeout(() => {
                        if (isEnterKeyPressed) {
                            console.log('📝 Processing Enter event after timeout:', {
                                storedLineContent: `"${enterPressLineContent}"`,
                                storedLineContentTrimmed: `"${enterPressLineContent.trim()}"`,
                                storedLineNumber: enterPressLineNumber,
                                hasStoredContent: enterPressLineContent.trim().length > 0
                            })
                            
                            // Track the enter event with the stored line content
                            const meaningfulContent = enterPressLineContent.trim()
                            const currentCode = view.value.state.doc.toString()
                            trackEnterEvent(meaningfulContent, enterPressLineNumber, selectedLanguage.value, currentCode)
                            
                            // Reset the flag
                            isEnterKeyPressed = false
                            enterPressLineContent = ''
                            enterPressLineNumber = -1
                        }
                    }, 10) // Small delay to let Enter processing complete
                }
            })
        }

        const sendProblemToBackend = (problem) => {
            if (!problem) return
            
            socket.emit('problem_update', {
                room: roomId,
                problemTitle: problem.title,
                problemDescription: problem.description + 
                    (problem.examples ? '\n\nExamples:\n' + 
                    problem.examples.map((ex, i) => 
                        `Example ${i+1}:\nInput: ${ex.input}\nOutput: ${ex.output}` + 
                        (ex.explanation ? `\nExplanation: ${ex.explanation}` : '')
                    ).join('\n\n') : '') +
                    (problem.constraints ? '\n\nConstraints:\n' + 
                    problem.constraints.join('\n') : '')
            })
        }

        const onProblemChanged = (data) => {
            console.log('Problem changed:', data.problem.title)
            
            // Store current problem
            currentProblem.value = data.problem
            
            // Send problem description to backend for AI agent
            sendProblemToBackend(data.problem)
        }

        const onBoilerplateChanged = (boilerplate) => {
            if (boilerplate) {
                code.value = boilerplate;
            }
        }

        // Broadcast current cursor position to other users
        const broadcastCursor = debounce(() => {
            if (view.value && !isReadOnly.value) {
                const selection = view.value.state.selection.main
                console.log('Broadcasting cursor:', { from: selection.from, to: selection.to })
                socket.emit('cursor', {
                    room: roomId,
                    userId: socket.id,
                    from: selection.from,
                    to: selection.to
                })
            }
        }, 200)

        // Broadcast current selection to other users
        const broadcastSelection = debounce(() => {
            if (view.value && !isReadOnly.value) {
                const selection = view.value.state.selection.main
                const userColor = codeMirrorExtensions.generateUserColor(socket.id, false) // false = not remote, it's me
                if (selection.from !== selection.to) { // Only broadcast if there's an actual selection
                    console.log('Broadcasting selection:', selection.from, 'to', selection.to)
                    socket.emit('selection', {
                        room: roomId,
                        userId: socket.id,
                        from: selection.from,
                        to: selection.to,
                        color: userColor.color,
                        classIndex: userColor.classIndex
                    })
                } else {
                    // Clear selection if no text is selected
                    socket.emit('selection', {
                        room: roomId,
                        userId: socket.id,
                        from: 0,
                        to: 0,
                        color: userColor.color,
                        classIndex: userColor.classIndex
                    })
                }
            }
        }, 100)

        // Make broadcasting functions available globally for extensions
        window.broadcastCursor = broadcastCursor
        window.broadcastSelection = broadcastSelection

        const handleCodeChange = (value, viewUpdate) => {
            console.log('handleCodeChange called with value length:', value.length)
            console.log('ViewUpdate docChanged:', viewUpdate.docChanged)
            
            if (isLocalUpdate.value) {
                console.log('🔄 Local update flag set, skipping analysis')
                return
            }
            
            // Only emit code_change and trigger analysis for actual document content changes
            // not just cursor position adjustments or remote cursor updates
            if (viewUpdate.docChanged) {
                console.log('📝 Document content changed - processing code update')
                
                isLocalUpdate.value = true
                code.value = value
                
                // Save to localStorage for persistence across reloads
                saveRoomState(value, selectedLanguage.value)
                
                // Emit code change to other users in the room
                socket.emit('code_change', {
                    room: roomId,
                    code: value,
                    userId: currentUserId.value,
                    language: selectedLanguage.value
                })
                
                // Monitor for code analysis
                if (viewUpdate.view) {
                    console.log('👀 Calling onCursorActivity with view')
                    codeAnalysis.onCursorActivity(viewUpdate.view)
                } else {
                    console.log('❌ No view in viewUpdate, skipping cursor activity')
                }
            } else {
                console.log('👁️ Only cursor/selection changed - skipping backend update and analysis')
                // Still update local code value for consistency
                code.value = value
            }
            
            isLocalUpdate.value = false
        }

        // Handle chat message from CodeRunner
        const handleCodeRunnerChatMessage = (message) => {
            // Forward the message to ChatContainer component
            if (chatContainer.value) {
                chatContainer.value.addMessage(message);
            }
        }

        // Handle personal AI message from CodeRunner
        const handleCodeRunnerPersonalAI = (messageData) => {
            console.log('🤖 Sending CodeRunner message directly to personal AI:', messageData.content)
            
            // Directly access the PairChat component through ChatContainer
            if (chatContainer.value && chatContainer.value.pairChat) {
                // Add @AI mention to the message content for proper AI triggering
                const messageWithAIMention = `@AI ${messageData.content}`
                
                // Set the message in the input field and send it
                chatContainer.value.pairChat.newMessage = messageWithAIMention
                chatContainer.value.pairChat.sendMessage()
                
                console.log('✅ Successfully sent CodeRunner message to personal AI with @AI mention')
            } else {
                console.error('❌ ChatContainer or PairChat reference not available')
            }
        }

        // Handle AI mode change from header toggle
        const handleAIModeChanged = (data) => {
            // Update local AI mode tracking
            currentAIMode.value = data.mode
            
            // Forward the mode change to ChatContainer
            if (chatContainer.value) {
                chatContainer.value.handleModeChanged(data)
            }
        }

        // Handle chat session state changes
        const handleChatSessionStateChanged = (data) => {
            console.log('🔄 Chat session state changed:', data)
            chatSessionStarted.value = data.sessionStarted
        }

        // Track Enter key events with improved approach
        const trackEnterEvent = async (currentLine, lineNumber, language, fullCode) => {
            try {
                console.log('📤 Sending enter event data:', {
                    room_id: roomId,
                    current_line: `"${currentLine}"`, // Add quotes to see empty strings
                    current_line_length: currentLine?.length || 0,
                    line_number: lineNumber,
                    language: language,
                    user_id: currentUserId.value,
                    full_code_length: fullCode?.length || 0,
                    full_code_preview: fullCode?.substring(0, 100) + (fullCode?.length > 100 ? '...' : ''),
                    is_empty: currentLine?.length === 0
                })
                
                const response = await fetch('/api/track-enter-event', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        room_id: roomId,
                        current_line: currentLine,
                        line_number: lineNumber,
                        language: language,
                        user_id: currentUserId.value,
                        full_code: fullCode
                    })
                })
                
                const result = await response.json()
                if (result.success) {
                    console.log('✅ Enter event tracked:', result.message)
                    console.log('📊 Tracked data confirmation:', result.tracked_data)
                } else {
                    console.error('❌ Failed to track enter event:', result.error)
                }
            } catch (error) {
                console.error('❌ Error tracking enter event:', error)
            }
        }

        // Watch for socket ID changes (reconnections)
        watch(() => socket.id, (newId) => {
            if (newId) {
                currentUserId.value = newId
                console.log('Socket ID updated:', newId)
            }
        })

        // Watch for language changes and save to localStorage
        watch(selectedLanguage, (newLanguage) => {
            console.log('📁 Language changed to:', newLanguage)
            saveRoomState(code.value, newLanguage)
        })

        onMounted(() => {
            connect()
            
            // Setup socket handlers
            socketHandlers.setupSocketHandlers()
            scaffolding.handleScaffoldingSocketEvents()
            
            // Session state synchronization
            socket.on('session_state_changed', (data) => {
                console.log('🔄 PairRoomView: Session state changed:', data)
                reflectionSession.handleSessionStateChange(data)
            })

            return () => {
                // Cleanup
                socketHandlers.cleanupSocketHandlers()
                scaffolding.cleanupScaffoldingSocketEvents()
                socket.off('session_state_changed')
                
                // Clean up keyboard event listener
                if (view.value && view.value.dom) {
                    view.value.dom.removeEventListener('keydown', codeAnalysis.handleKeyDown)
                }
            }
        })

        // Code Analysis Popup Handlers
        const handlePopupAnalyze = (codeBlock) => {
            console.log('🔍 Popup analyze triggered for code block:', codeBlock)
            // Close the popup
            showCodeAnalysisPopup.value = false
            
            // Trigger the analysis using the existing code analysis system
            codeAnalysis.scheduleCodeAnalysis(codeBlock)
        }

        const handlePopupClose = () => {
            showCodeAnalysisPopup.value = false
            popupCodeBlock.value = null
        }

        // Function to show popup at a specific position (will be called from CodeMirror extension)
        const showCodeAnalysisPopupAt = (position, codeBlock) => {
            popupPosition.value = position
            popupCodeBlock.value = codeBlock
            showCodeAnalysisPopup.value = true
        }

        // Make the popup function globally available for CodeMirror extensions
        window.showCodeAnalysisPopup = showCodeAnalysisPopupAt

        // TODO Reveal Popup Handlers
        const handleTodoReveal = async (todoData) => {
            console.log('🎯 TODO reveal triggered for:', todoData)
            // Close the popup
            showTodoRevealPopup.value = false
            
            try {
                // Call the backend API to get the generated code
                const response = await fetch('/api/reveal-todo', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        code: todoData.code,
                        language: todoData.language,
                        cursorLine: todoData.cursorLine,
                        roomId: roomId,
                        problemContext: currentProblem.value?.description || ''
                    })
                })
                
                const result = await response.json()
                
                if (result.success && result.generatedCode) {
                    console.log('✅ Generated TODO code:', result.generatedCode)
                    
                    // Replace the TODO line with the generated code in the editor
                    if (view.value) {
                        const doc = view.value.state.doc
                        const line = doc.line(todoData.cursorLine + 1) // Convert back to 1-based
                        
                        // Apply indentation to the generated code line
                        const todoLineText = line.text
                        const indentMatch = todoLineText.match(/^(\s*)/)
                        const indent = indentMatch ? indentMatch[1] : ''
                        
                        // Apply same indentation to generated code
                        const indentedCode = indent + result.generatedCode.trim()
                        
                        // Replace the TODO line with the generated code
                        view.value.dispatch({
                            changes: {
                                from: line.from,
                                to: line.to,
                                insert: indentedCode
                            }
                        })
                        
                        console.log('📝 Replaced TODO line with generated code')
                    }
                } else {
                    console.error('❌ Failed to generate TODO code:', result.message || 'Unknown error')
                }
            } catch (error) {
                console.error('❌ Error calling TODO reveal API:', error)
            }
        }

        const handleTodoPopupClose = () => {
            showTodoRevealPopup.value = false
            todoData.value = null
        }

        const handleTodoAnalyze = (codeBlock) => {
            console.log('🔍 TODO Analyze triggered for code block:', codeBlock)
            // Close TODO popup
            showTodoRevealPopup.value = false
            // Show code analysis popup instead
            popupPosition.value = todoPopupPosition.value
            popupCodeBlock.value = codeBlock
            showCodeAnalysisPopup.value = true
        }

        // Function to show TODO popup at a specific position (will be called from CodeMirror extension)
        const showTodoRevealPopupAt = (position, todoInfo) => {
            todoPopupPosition.value = position
            todoData.value = todoInfo
            showTodoRevealPopup.value = true
        }

        // Make the TODO popup function globally available for CodeMirror extensions
        window.showTodoRevealPopup = showTodoRevealPopupAt

        return {
            code,
            selectedLanguage,
            extensions,
            view,
            isReadOnly,
            roomId,
            currentUserId,
            currentProblem,
            selectedProblem,
            chatSessionStarted,
            currentAIMode,
            computedExtensions: codeMirrorExtensions.computedExtensions,
            socket,
            handleReady,
            handleCodeChange,
            updateLanguage,
            onProblemChanged,
            onBoilerplateChanged,
            auth,
            
            // Code analysis from composable
            showCodeAnalysis: codeAnalysis.showCodeAnalysis,
            currentCodeBlock: codeAnalysis.currentCodeBlock,
            onHighlightLine: codeAnalysis.onHighlightLine,
            onApplyFix: codeAnalysis.onApplyFix,
            onExplainIssue: codeAnalysis.onExplainIssue,
            onCodeAnalysisDismissed: codeAnalysis.onCodeAnalysisDismissed,
            onIssuesFound: codeAnalysis.onIssuesFound,
            
            // Scaffolding from composable
            showScaffoldingNotification: scaffolding.showScaffoldingNotification,
            scaffoldingNotificationText: scaffolding.scaffoldingNotificationText,
            
            // Reflection session from composable
            showReflectionSession: reflectionSession.showReflectionSession,
            reflectionSessionId: reflectionSession.reflectionSessionId,
            startReflectionSession: reflectionSession.startReflectionSession,
            stopReflectionSession: reflectionSession.stopReflectionSession,
            endReflectionSession: reflectionSession.endReflectionSession,
            
            // Chat handling
            handleCodeRunnerChatMessage,
            handleCodeRunnerPersonalAI,
            handleAIModeChanged,
            handleChatSessionStateChanged,
            handleReflectionSessionStarted: reflectionSession.handleReflectionSessionStarted,
            handleReflectionSessionEnded: reflectionSession.handleReflectionSessionEnded,
            chatContainer,
            
            // Code Analysis Popup
            showCodeAnalysisPopup,
            popupPosition,
            popupCodeBlock,
            handlePopupAnalyze,
            handlePopupClose,
            
            // TODO Reveal Popup
            showTodoRevealPopup,
            todoPopupPosition,
            todoData,
            handleTodoReveal,
            handleTodoAnalyze,
            handleTodoPopupClose,
        }
    }
})
</script>

<style scoped>
.editor-container {
    height: 100vh;
    background: #f8fafc;
    display: flex;
    flex-direction: column;
}

.editor-header {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid rgba(0, 0, 0, 0.1);
    padding: 0.75rem 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.header-content h1 {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
    color: #2d3748;
}

.room-title {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
    color: #2d3748;
}

.highlight-together {
    color: #667eea;
    font-weight: 600;
}

.highlight-personal {
    color: #48bb78;
    font-weight: 600;
}

.powered-by {
    color: #4a5568;
    font-size: 0.65rem;
    margin: 0.15rem 0 0 0;
    font-style: italic;
    letter-spacing: 0.5px;
}

.room-id {
    margin: 0.25rem 0 0 0;
    font-size: 0.875rem;
    color: #718096;
    font-weight: 500;
}

.controls {
    display: flex;
    align-items: center;
    gap: 1.5rem;
}

.ai-mode-control {
    display: flex;
    align-items: center;
}

.language-selector {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.language-selector label {
    font-weight: 500;
    color: #4a5568;
    font-size: 0.875rem;
}

.language-selector select {
    padding: 0.5rem 1rem;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    background: white;
    color: #2d3748;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    min-width: 140px;
}

.language-selector select:hover {
    border-color: #4f46e5;
}

.language-selector select:focus {
    outline: none;
    border-color: #4f46e5;
    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.mode-toggle {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.switch {
    position: relative;
    display: inline-block;
    width: 50px;
    height: 24px;
}

.switch input {
    opacity: 0;
    width: 0;
    height: 0;
}

.slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: #cbd5e0;
    transition: 0.3s;
    border-radius: 24px;
}

.slider:before {
    position: absolute;
    content: "";
    height: 18px;
    width: 18px;
    left: 3px;
    bottom: 3px;
    background-color: white;
    transition: 0.3s;
    border-radius: 50%;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

input:checked + .slider {
    background: linear-gradient(135deg, #667eea, #764ba2);
}

input:checked + .slider:before {
    transform: translateX(26px);
}

.mode-label {
    font-weight: 500;
    color: #4a5568;
    font-size: 0.875rem;
    cursor: pointer;
}

.editor-wrapper {
    flex: 1;
    height: 100%;
    max-height: 100%;
    overflow-y: auto;
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.main-content {
    flex: 1;
    display: flex;
    gap: 1rem;
    padding: 1rem;
    min-height: 0;
}

.left-panel {
    width: 400px;
    flex-shrink: 0;
}

.center-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    height: 85vh;
    min-height: 0;
    min-width: 0;
}

.right-panel {
    width: 450px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.code-editor {
    height: 100%;
    font-size: 14px;
    line-height: 1.5;
}

/* Debug button styles */
.debug-btn {
    background: #6366f1;
    color: white;
    border: none;
    padding: 6px 12px;
    border-radius: 4px;
    font-size: 12px;
    margin-left: 8px;
    cursor: pointer;
    transition: background-color 0.2s;
}

.debug-btn:hover {
    background: #4f46e5;
}

.debug-btn:active {
    background: #3730a3;
}

/* Small Scaffolding Notification */
.scaffolding-notification {
    position: fixed;
    top: 20px;
    right: 20px;
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    padding: 12px 16px;
    border-radius: 8px;
    box-shadow: 0   4px 12px rgba(0, 0, 0, 0.15);
    z-index: 1000;
    max-width: 300px;
    animation: slideInRight 0.3s ease-out;
}

.notification-content {
    display: flex;
    align-items: center;
    gap: 8px;
}

.notification-icon {
    font-size: 16px;
}

.notification-text {
    font-size: 14px;
    font-weight: 500;
    line-height: 1.4;
}

/* AI Status Section with Small Reflection Button */
.ai-status-section {
    width: 100%;
    margin-bottom: 0.5rem;
}

/* Responsive design */
@media (max-width: 1200px) {
    .left-panel {
        width: 300px;
    }
    
    .right-panel {
        width: 280px;
    }
}

@media (max-width: 768px) {
    .editor-header {
        flex-direction: column;
        gap: 1rem;
        align-items: flex-start;
        padding: 1rem;
    }
    
    .controls {
        flex-direction: column;
        gap: 1rem;
        width: 100%;
    }
    
    .main-content {
        flex-direction: column;
        padding: 0.5rem;
    }
    
    .left-panel, .right-panel {
        width: 100%;
        max-height: 300px;
    }
    
    .code-editor {
        height: 500px;
    }
}

@keyframes slideInRight {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

/* Critical scoped styles that need :deep() for cursor/selection functionality */

/* Remote selection styling - using :deep() for scoped CSS penetration */
:deep([class*="remote-selection-"]) {
    background-color: rgba(147, 51, 234, 0.25) !important; /* Light purple */
    border: 1px solid rgba(147, 51, 234, 0.4) !important;
    border-radius: 3px;
    backdrop-filter: blur(1px);
}

/* Remote cursor styles - keep original red color with :deep() */
:deep(.remote-cursor) {
    position: relative !important;
    display: inline-block !important;
    width: 2px !important;
    height: 1em !important;
    background: #ef4444 !important; /* Keep red cursor */
    border-radius: 1px !important;
    margin-left: -1px !important;
    pointer-events: none !important;
    z-index: 45 !important;
    opacity: 1 !important;
    animation: cursor-blink 1s infinite;
}

/* All remote cursors use the same red color */
:deep([class*="remote-cursor-"]) {
    position: relative !important;
    display: inline-block !important;
    width: 2px !important;
    height: 1em !important;
    background: #ef4444 !important; /* Keep red cursor */
    border-radius: 1px !important;
    margin-left: -1px !important;
    pointer-events: none !important;
    z-index: 45 !important;
    opacity: 1 !important;
    animation: cursor-blink 1s infinite;
}

/* Dynamic user-specific selections based on socket ID hash */
:deep(.cm-editor) [class*="remote-selection-"] {
    position: relative;
    z-index: 1;
}

/* Also ensure cursor styles work within CodeMirror */
:deep(.cm-editor) [class*="remote-cursor-"] {
    position: relative !important;
    z-index: 45 !important;
}

/* CodeMirror overrides for better light theme */
:deep(.cm-editor) {
    border-radius: 12px;
    border: 1px solid #e2e8f0;
}

:deep(.cm-focused) {
    outline: none;
}

:deep(.cm-editor.cm-focused) {
    border-color: #4f46e5;
    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

:deep(.cm-scroller) {
    font-family: 'Fira Code', 'Monaco', 'Menlo', monospace;
}

:deep(.cm-gutters) {
    background-color: #f8fafc;
    border-right: 1px solid #e2e8f0;
    border-radius: 12px 0 0 12px;
}

:deep(.cm-activeLineGutter) {
    background-color: #edf2f7;
}

:deep(.cm-activeLine) {
    background-color: rgba(79, 70, 229, 0.05);
}

/* Global styles that need to work outside component scope */
:global(.code-analysis-line-indicator) {
    position: absolute;
    left: -2px;
    top: 0;
    bottom: 0;
    width: 4px;
    border-radius: 2px;
    pointer-events: none;
    opacity: 0.8;
    z-index: 10;
    transition: opacity 0.2s ease;
    animation: codeAnalysisSlideIn 0.3s ease-out;
}

:global(.code-analysis-line-indicator.severity-high) {
    background: #dc3545;
    box-shadow: 0 0 4px rgba(220, 53, 69, 0.4);
}

:global(.code-analysis-line-indicator.severity-medium) {
    background: #ffc107;
    box-shadow: 0 0 4px rgba(255, 193, 7, 0.4);
}

:global(.code-analysis-line-indicator.severity-low) {
    background: #28a745;
    box-shadow: 0 0 4px rgba(40, 167, 69, 0.4);
}

:global(.cm-editor:hover .code-analysis-line-indicator) {
    opacity: 1;
}

:global(.code-analysis-line-mark) {
    position: relative;
    transition: all 0.3s ease;
}

:global(.code-analysis-line-mark.severity-high) {
    border-left: 4px solid #dc3545 !important;
}

:global(.code-analysis-line-mark.severity-medium) {
    border-left: 4px solid #ffc107 !important;
}

:global(.code-analysis-line-mark.severity-low) {
    border-left: 4px solid #28a745 !important;
}

:global(.code-analysis-line-mark.analyzing) {
    border-left: 3px solid #6c757d !important;
    opacity: 0.6;
    animation: analysisIndicatorPulse 2s ease-in-out infinite;
}

:global(.reflection-highlight-line) {
    background: linear-gradient(90deg, rgba(125, 211, 252, 0.15) 0%, rgba(125, 211, 252, 0.08) 100%) !important;
    border-left: 4px solid #38bdf8 !important;
    animation: reflectionHighlight 2s ease-in-out infinite;
}

/* Global animations */
@keyframes codeAnalysisSlideIn {
    from {
        transform: translateX(-10px);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 0.8;
    }
}

@keyframes analysisIndicatorPulse {
    0%, 100% { opacity: 0.6; }
    50% { opacity: 0.9; }
}

@keyframes reflectionHighlight {
    0%, 100% { 
        background: linear-gradient(90deg, rgba(125, 211, 252, 0.15) 0%, rgba(125, 211, 252, 0.08) 100%) !important;
    }
    50% { 
        background: linear-gradient(90deg, rgba(125, 211, 252, 0.25) 0%, rgba(125, 211, 252, 0.15) 100%) !important;
    }
}
</style>