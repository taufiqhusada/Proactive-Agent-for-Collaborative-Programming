<template>
    <div class="editor-container">
        <div class="editor-header">
            <div class="header-content">
                <h1 class="room-title">Collaborative Code Editor</h1>
                <!-- <p class="room-id">Room: {{ roomId }}</p> -->
            </div>
            <div class="controls">
                <div class="language-selector">
                    <label for="languageSelect">Language:</label>
                    <select id="languageSelect" v-model="selectedLanguage" @change="updateLanguage">
                        <option value="python">🐍 Python</option>
                        <option value="java">☕ Java</option>
                        <option value="cpp">⚡ C++</option>
                        <option value="javascript">🚀 JavaScript</option>
                    </select>
                </div>
                <div class="mode-toggle">
                    <label class="switch">
                        <input type="checkbox" v-model="isReadOnly" id="readOnlyMode">
                        <span class="slider"></span>
                    </label>
                    <label for="readOnlyMode" class="mode-label">Read-only Mode</label>
                </div>
            </div>
        </div>

        <div class="main-content">
            <!-- Left Panel: Problem Description -->
            <div class="left-panel">
                <ProblemDescription @problem-changed="onProblemChanged" />
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
                    @chat-message="handleCodeRunnerChatMessage"
                />
            </div>

            <!-- Right Panel: Chat -->
            <div class="right-panel">
                <AIAgentStatus />
                <PairChat 
                    ref="pairChat"
                    :socket="socket" 
                    :room-id="roomId" 
                    :current-user-id="currentUserId"
                    :username="auth?.user || 'Guest'" />
            </div>
        </div>
        
        <!-- Code Issue Analysis Panel -->
        <CodeIssuePanel 
            :visible="showCodeAnalysis"
            :code-block="currentCodeBlock"
            :editor-position="{ top: 100, left: 0 }"
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
    </div>
</template>

<script>
import { defineComponent, ref, shallowRef, onMounted, watch, computed } from 'vue'
import { Codemirror } from 'vue-codemirror'
import { javascript } from '@codemirror/lang-javascript'
import { python } from '@codemirror/lang-python'
import { java } from '@codemirror/lang-java'
import { cpp } from '@codemirror/lang-cpp'
import { EditorState, StateField, StateEffect } from '@codemirror/state'
import { EditorView, Decoration, WidgetType } from '@codemirror/view'
import { useRoute } from 'vue-router'
import { useSocket } from '@/lib/socket'
import { runCode } from '@/lib/runCode'
import { debounce } from 'lodash'
import { useAuth } from '@/stores/useAuth'
import ProblemDescription from '@/components/ProblemDescription.vue'
import PairChat from '@/components/PairChat.vue'
import AIAgentStatus from '@/components/AIAgentStatus.vue'
import CodeIssuePanel from '@/components/CodeIssuePanel.vue'
import CodeRunner from '@/components/CodeRunner.vue'

export default defineComponent({
    components: {
        Codemirror,
        ProblemDescription,
        PairChat,
        AIAgentStatus,
        CodeIssuePanel,
        CodeRunner,
    },

    setup() {
        const route = useRoute()
        const auth = useAuth()
        const roomId = String(route.params.roomId)
        const code = ref('print("Hello")')
        const output = ref('')
        const selectedLanguage = ref('python')
        const extensions = ref([python()])
        const view = shallowRef()
        const lastReceivedContent = ref('')
        const isReadOnly = ref(false)
        const isLocalUpdate = ref(false)
        const currentUserId = ref('')
        const currentProblem = ref(null)
        const { socket, connect } = useSocket()
        
        // Code analysis state
        const showCodeAnalysis = ref(false)
        const currentCodeBlock = ref(null)
        const lastAnalyzedHash = ref('')
        const analysisDebounceTimer = ref(null)
        const userTypingTimer = ref(null)
        const lastTypingTime = ref(0)
        
        // Scaffolding notification state
        const showScaffoldingNotification = ref(false)
        const scaffoldingNotificationText = ref('')
        
        // Enhanced detection state
        const consecutiveEnters = ref(0)
        const ENTER_THRESHOLD = 2

        const languages = {
            python: python(),
            java: java(),
            cpp: cpp(),
            javascript: javascript(),
        }

        // Effects for managing remote cursors
        const setRemoteCursor = StateEffect.define()
        const clearRemoteCursor = StateEffect.define()
        
        // Effects for managing code analysis line indicators
        const setCodeAnalysisLines = StateEffect.define()
        const clearCodeAnalysisLines = StateEffect.define()
        
        // Widget for displaying remote cursors
        class RemoteCursorWidget extends WidgetType {
            constructor(userId) {
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

            eq(other) {
                return other instanceof RemoteCursorWidget && other.userId === this.userId
            }
        }
        
        // Code Analysis Line Indicator Widget
        class CodeAnalysisLineWidget extends WidgetType {
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
                            
                            // Check if this decoration belongs to this user
                            const userColorInfo = generateUserColor(userId, true) // true = remote user
                            const isThisUserSelection = className.includes(`remote-selection-${userColorInfo.classIndex}`)
                            const isThisUserCursor = isWidget && widgetUserId === userId
                            
                            if (!isThisUserSelection && !isThisUserCursor) {
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
                                
                                // Check if this decoration belongs to this user
                                const userColorInfo = generateUserColor(userId, true) // true = remote user
                                const isThisUserSelection = className.includes(`remote-selection-${userColorInfo.classIndex}`)
                                const isThisUserCursor = isWidget && widgetUserId === userId
                                
                                return !isThisUserSelection && !isThisUserCursor
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

        const updateLanguage = () => {
            const newExtension = languages[selectedLanguage.value]
            extensions.value = [newExtension, ...(isReadOnly.value ? [EditorState.readOnly.of(true)] : [])]
        }

        // Extension to detect selection and cursor changes
        const selectionUpdateExtension = EditorView.updateListener.of((update) => {
            if ((update.selectionSet || update.focusChanged) && !isReadOnly.value) {
                // Only broadcast if this is a real user selection change, not a programmatic update
                if (!update.transactions.some(tr => tr.effects.some(e => e.is(setRemoteCursor)))) {
                    const selection = update.state.selection.main
                    if (selection.from !== selection.to) {
                        // Broadcast selection when text is selected
                        broadcastSelection()
                    } else {
                        // Broadcast cursor when just cursor position changes
                        broadcastCursor()
                    }
                }
            }
        })

        // Computed property for extensions that includes readonly state, remote cursors, and code analysis indicators
        const computedExtensions = computed(() => {
            const langExtension = languages[selectedLanguage.value]
            const baseExtensions = [langExtension, remoteCursorField, codeAnalysisField, selectionUpdateExtension]
            if (isReadOnly.value) {
                baseExtensions.push(EditorState.readOnly.of(true))
                baseExtensions.push(EditorView.editable.of(false))
            }
            return baseExtensions
        })

        const handleReady = (payload) => {
            view.value = payload.view
            
            // Add keyboard event listener for enhanced detection
            const editorDom = view.value.dom
            editorDom.addEventListener('keydown', handleKeyDown)
        }

        const execute = async () => {
            const res = await runCode(code.value)
            output.value = res.stderr || res.stdout || 'no output'
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
            
            // You can sync the problem selection across users if needed
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

        // Broadcast current selection to other users
        const broadcastSelection = debounce(() => {
            if (view.value && !isReadOnly.value) {
                const selection = view.value.state.selection.main
                const userColor = generateUserColor(socket.id, false) // false = not remote, it's me
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

        // Handle remote selection updates
        const handleRemoteSelection = (data) => {
            console.log('handleRemoteSelection called with:', data)
            if (data.userId !== socket.id && view.value) {
                console.log('Processing remote selection from different user')
                try {
                    if (data.from !== data.to && 
                        typeof data.from === 'number' && 
                        typeof data.to === 'number' && 
                        data.from >= 0 && 
                        data.to >= 0) {
                        
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
                        console.log('Clearing remote selection (no valid selection)')
                        view.value.dispatch({
                            effects: [clearRemoteCursor.of(data.userId)]
                        })
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

        const handleRemoteCodeExecution = (data) => {
            console.log('📡 Handling remote code execution:', data)
            
            // Add a visual notification that someone else ran code
            addChatMessage({
                id: 'exec_' + Date.now(),
                content: `🚀 User ${data.user_id.slice(-4)} executed code`,
                username: 'System',
                userId: 'system',
                timestamp: new Date().toISOString(),
                room: roomId,
                isAutoGenerated: true,
                isSystemMessage: true,
                executionData: {
                    code: data.code,
                    language: data.language,
                    result: data.result,
                    timestamp: data.timestamp
                }
            })

            // Show a toast notification
            showExecutionNotification(data)
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

        // Watch for code changes as a fallback
        watch(code, (newValue, oldValue) => {
            console.log('👀 Code watcher triggered - new length:', newValue.length, 'old length:', oldValue?.length || 0)
            
            if (newValue !== oldValue && !isLocalUpdate.value) {
                console.log('🔍 Code changed, starting analysis timer...')
                
                // Clear existing timer
                if (userTypingTimer.value) {
                    clearTimeout(userTypingTimer.value)
                }
                
                // Set new timer - wait for user to stop typing
                userTypingTimer.value = setTimeout(() => {
                    console.log('⏰ Code watcher timer expired, analyzing...')
                    
                    if (view.value) {
                        const cursor = view.value.state.selection.main.head
                        const cursorPos = view.value.state.doc.lineAt(cursor)
                        onUserStoppedTyping(view.value, { line: cursorPos.number - 1, ch: cursor - cursorPos.from })
                    }
                }, 2000)
            }
        })
        
        // Prevent code changes in readonly mode
        const handleCodeChange = (value, viewUpdate) => {
            console.log('handleCodeChange called with value length:', value.length)
            
            if (isLocalUpdate.value) {
                console.log('🔄 Local update flag set, skipping analysis')
                return
            }
            
            isLocalUpdate.value = true
            code.value = value
            
            // Emit code change to other users in the room
            socket.emit('code_change', {
                room: roomId,
                code: value,
                userId: currentUserId.value,
                language: selectedLanguage.value
            })
            
            // Update room state - handled by backend
            
            // Monitor for code analysis
            if (viewUpdate.view) {
                console.log('👀 Calling onCursorActivity with view')
                onCursorActivity(viewUpdate.view)
            } else {
                console.log('❌ No view in viewUpdate, skipping cursor activity')
            }
            
            isLocalUpdate.value = false
        }

        const handleCodeUpdate = (value, viewUpdate) => {
            console.log('🔄 handleCodeUpdate called with value length:', value.length)
            handleCodeChange(value, viewUpdate)
        }
        
        // Watch for socket ID changes (reconnections)
        watch(() => socket.id, (newId) => {
            if (newId) {
                currentUserId.value = newId
                console.log('Socket ID updated:', newId)
            }
        })

        onMounted(() => {
            connect()
            
            // Wait for connection before joining room
            socket.on('connect', () => {
                // Update current user ID when socket connects
                currentUserId.value = socket.id
                console.log('Socket connected with ID:', socket.id)
                
                socket.emit('join', { room: roomId }, (response) => {
                    if (response && response.code) {
                        lastReceivedContent.value = response.code
                        isLocalUpdate.value = true
                        code.value = response.code
                    }
                    
                    // Send initial problem description to backend after joining
                    setTimeout(() => {
                        if (currentProblem.value) {
                            sendProblemToBackend(currentProblem.value)
                        }
                    }, 1000) // Wait 1 second to ensure problem component is mounted
                })
            })

            socket.on('update', ({ delta, sourceId }) => {
                if (sourceId !== socket.id) {
                    lastReceivedContent.value = delta
                    isLocalUpdate.value = true
                    code.value = delta
                }
            })

            socket.on('cursor', (data) => {
                handleRemoteCursor(data)
            })

            socket.on('selection', (data) => {
                handleRemoteSelection(data)
            })
            
            socket.on('user_disconnected', (data) => {
                if (view.value) {
                    view.value.dispatch({
                        effects: [clearRemoteCursor.of(data.userId)]
                    })
                }
            })

            socket.on('code_execution_result', (data) => {
                console.log('📡 Received code execution from another user:', data)
                handleRemoteCodeExecution(data)
            })

            socket.on('connect_error', (error) => {
                console.error('Socket connection error:', error)
            })
            
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

            return () => {
                socket.off('connect')
                socket.off('update')
                socket.off('cursor')
                socket.off('selection')
                socket.off('user_disconnected')
                socket.off('code_execution_result')
                socket.off('connect_error')
                socket.off('scaffolding-lock-request')
                socket.off('scaffolding-lock-acquired')
                socket.off('scaffolding-completed')
                socket.off('scaffolding-lock-released')
                socket.emit('leave', { room: roomId })
                
                // Clean up keyboard event listener
                if (view.value && view.value.dom) {
                    view.value.dom.removeEventListener('keydown', handleKeyDown)
                }
            }
        })

        // Code analysis functions
        const extractCurrentCodeBlock = (editor, cursor) => {
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
        
        const getIndentLevel = (lineText) => {
            const match = lineText.match(/^(\s*)/)
            return match ? match[1].length : 0
        }
        
        const isBlockStart = (lineText) => {
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
        
        const shouldAnalyzeCodeBlock = (codeBlock) => {
            console.log('🔍 Checking code block significance...')
            console.log('📊 Code:', codeBlock.code)
            console.log('📏 Code length:', codeBlock.code.length)
            
            // Check if block is significant enough to analyze
            const lines = codeBlock.code.split('\n').filter(line => line.trim().length > 0)
            const chars = codeBlock.code.replace(/\s/g, '').length
            
            console.log('📋 Lines:', lines.length, 'Characters:', chars)
            
            // Relaxed size check for educational coding - either condition is enough
            if (lines.length < 3 && chars < 50) {
                console.log('❌ Failed size check: lines < 3 AND chars < 50')
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
        
        const hashCode = (str) => {
            let hash = 0
            for (let i = 0; i < str.length; i++) {
                const char = str.charCodeAt(i)
                hash = ((hash << 5) - hash) + char
                hash = hash & hash // Convert to 32-bit integer
            }
            return hash
        }
        
        // Enhanced detection functions
        const handleKeyDown = (event) => {
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
        
        const triggerImmediateAnalysis = (editor, cursor) => {
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
        
        const findPreviousCodeBlock = (editor, cursor) => {
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
        
        const onCursorActivity = (editor) => {
            console.log('🔍 onCursorActivity triggered')
            
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
            
            console.log('⏱️ Setting 2-second timer for code analysis')
            
            // Set new timer - wait for user to stop typing
            userTypingTimer.value = setTimeout(() => {
                console.log('⏰ Timer expired, analyzing code...')
                onUserStoppedTyping(editor, { line: cursorPos.number - 1, ch: cursor - cursorPos.from })
            }, 2000) // 2 seconds of inactivity
        }
        
        const onUserStoppedTyping = (editor, cursor) => {
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
        
        const scheduleCodeAnalysis = (codeBlock) => {
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
            
            // Show immediate feedback that analysis is starting (subtle analyzing indicators)
            if (codeBlock && typeof codeBlock.startLine === 'number' && typeof codeBlock.endLine === 'number') {
                showCodeAnalysisLineIndicators(codeBlock.startLine, codeBlock.endLine, 'analyzing')
                console.log('� Showing analysis-in-progress indicators')
            } else {
                console.warn('⚠️ Invalid codeBlock line numbers for indicators:', codeBlock)
            }
            
            currentCodeBlock.value = enhancedCodeBlock
            showCodeAnalysis.value = true
            console.log('✅ Code analysis panel should be visible now')
        }
        
        const onHighlightLine = (lineNumber) => {
            // Highlight the problematic line in the editor
            if (view.value) {
                const line = view.value.state.doc.line(lineNumber)
                view.value.dispatch({
                    selection: { anchor: line.from, head: line.to },
                    scrollIntoView: true
                })
            }
        }
        
        const onApplyFix = (issue) => {
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
        
        const onExplainIssue = (issue) => {
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
            
            // Clear the line indicators when analysis panel is dismissed
            if (view.value) {
                clearCodeAnalysisLineIndicators()
            }
            
            console.log('🔄 Analysis panel dismissed and line indicators cleared')
        }
        
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
        
        // Make test functions available globally for debugging
        window.testCodeAnalysis = testCodeAnalysis
        
        // Simple test function to add a very visible indicator
        const testVisibleIndicator = () => {
            console.log('🎨 Testing highly visible indicator...')
            
            if (!view.value) {
                console.log('❌ Editor not ready')
                return
            }
            
            // Add a very obvious visual indicator to the first line
            const firstLine = document.querySelector('.cm-line')
            if (firstLine) {
                firstLine.style.borderLeft = '10px solid red'
                firstLine.style.backgroundColor = 'rgba(255, 0, 0, 0.2)'
                firstLine.style.paddingLeft = '20px'
                console.log('✅ Added direct CSS to first line:', firstLine)
                
                // Remove after 3 seconds
                setTimeout(() => {
                    firstLine.style.borderLeft = ''
                    firstLine.style.backgroundColor = ''
                    firstLine.style.paddingLeft = ''
                    console.log('🧹 Removed direct CSS')
                }, 3000)
            } else {
                console.log('❌ No .cm-line elements found')
            }
        }
        
        // Handle chat message from CodeRunner
        const handleCodeRunnerChatMessage = (message) => {
            // Forward the message to PairChat component
            if (pairChat.value) {
                pairChat.value.addMessage(message);
            }
        }
        
        // Create ref for PairChat component
        const pairChat = ref(null)
        
        // ========================
        // SIMPLIFIED SCAFFOLDING FUNCTIONALITY
        // ========================
        
        const scaffoldingTimer = ref(null)
        const processedComments = ref(new Set()) // Track already processed comments
        const lastProcessedComment = ref('') // Track the last comment we processed
        const activeScaffoldingRequests = ref(new Set()) // Track ongoing scaffolding requests across users
        const scaffoldingLocks = ref(new Map()) // Track who is processing which comment
        
        const detectScaffoldingTrigger = (newCode, oldCode) => {
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
                
                // Check if line starts with comment and has content
                const commentPrefixes = {
                    'python': '#',
                    'javascript': '//',
                    'java': '//',
                    'cpp': '//'
                }
                
                const prefix = commentPrefixes[selectedLanguage.value] || '#'
                
                // Check if line starts with comment and has content
                if (line.startsWith(prefix) && line.length > prefix.length + 1) {
                    // Skip TODO comments - these are typically generated by scaffolding
                    const commentContent = line.substring(prefix.length).trim().toLowerCase()
                    if (commentContent.startsWith('todo:') || commentContent.startsWith('todo ')) {
                        console.log('🚫 Skipping TODO comment (likely from scaffolding):', line)
                        return
                    }
                    
                    // Skip other common non-scaffolding comments
                    const skipPatterns = [
                        'fixme:', 'hack:', 'note:', 'warning:', 'bug:', 'deprecated:',
                        'end of', 'start of', 'this is', 'this will', 'this should'
                    ]
                    
                    if (skipPatterns.some(pattern => commentContent.includes(pattern))) {
                        console.log('🚫 Skipping descriptive comment:', line)
                        return
                    }
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
                    
                    console.log('🏗️ Comment detected, starting 2s timer:', line)
                    
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
        
        const attemptScaffoldingLock = (code, cursorLine, commentId) => {
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
        
        const requestScaffolding = async (code, cursorLine, commentId) => {
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
                        cursorLine: cursorLine
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
        
        const showScaffoldingSuggestion = (scaffoldingResult, lineNumber) => {
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
                
                // Send notification to chat
                addChatMessage({
                    id: 'scaffolding_applied_' + Date.now(),
                    content: `🏗️ Applied scaffolding for: "${scaffoldingResult.originalComment}"`,
                    username: 'Scaffolding Assistant',
                    userId: 'scaffolding_system',
                    timestamp: new Date().toISOString(),
                    room: roomId,
                    isAutoGenerated: true,
                    isSystemMessage: true,
                    scaffoldingData: {
                        originalComment: scaffoldingResult.originalComment,
                        language: scaffoldingResult.language
                    }
                })
                
                console.log('✅ Auto-inserted scaffolding below comment')
            }
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
        
        // ========================
        // END SCAFFOLDING FUNCTIONALITY
        // ========================
         // Helper functions for managing code analysis line indicators
        const showCodeAnalysisLineIndicators = (startLine, endLine, severity = 'medium') => {
            if (!view.value || !view.value.state || !view.value.dispatch) {
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
                view.value.dispatch({
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
        
        const clearCodeAnalysisLineIndicators = () => {
            if (!view.value || !view.value.dispatch) {
                console.warn('⚠️ Editor view not ready for clearing indicators')
                return
            }
            
            console.log('🔄 Clearing code analysis line indicators')
            
            try {
                view.value.dispatch({
                    effects: clearCodeAnalysisLines.of()
                })
            } catch (error) {
                console.error('❌ Error clearing line indicators:', error)
            }
        }
        
        const updateCodeAnalysisLineIndicators = (startLine, endLine, severity = 'medium') => {
            // Clear existing indicators and show new ones
            clearCodeAnalysisLineIndicators()
            // Add a small delay to ensure clearing completes
            setTimeout(() => {
                showCodeAnalysisLineIndicators(startLine, endLine, severity)
            }, 10)
        }
        
        const onIssuesFound = (data) => {
            if (!data || typeof data !== 'object') {
                console.warn('⚠️ Invalid data received in onIssuesFound:', data)
                return
            }
            
            const { codeBlock, issues, highestSeverity } = data
            
            console.log(`🎯 Issues found with severity ${highestSeverity}:`, issues)
            
            // Update line indicators with the severity based on analysis results
            if (codeBlock && codeBlock.startLine && codeBlock.endLine && 
                typeof codeBlock.startLine === 'number' && typeof codeBlock.endLine === 'number') {
                updateCodeAnalysisLineIndicators(
                    codeBlock.startLine, 
                    codeBlock.endLine, 
                    highestSeverity || 'medium'
                )
            } else {
                console.warn('⚠️ Invalid codeBlock data for line indicators:', codeBlock)
            }
        }
        
        // Test function for line indicators
        const testLineIndicators = () => {
            console.log('🧪 Testing line indicators...')
            
            if (!view.value) {
                console.log('❌ Editor view not available - waiting for editor to load')
                // Try again after a short delay
                setTimeout(() => {
                    if (view.value) {
                        console.log('✅ Editor now available, retrying...')
                        testLineIndicators()
                    } else {
                        console.log('❌ Editor still not available after delay')
                    }
                }, 1000)
                return
            }
            
            console.log('📍 Showing test indicators on lines 1-3')
            showCodeAnalysisLineIndicators(1, 3, 'high')
            
            // Check if elements exist in DOM after a short delay
            setTimeout(() => {
                const elements = document.querySelectorAll('.code-analysis-line-mark')
                console.log(`🔍 Found ${elements.length} .code-analysis-line-mark elements in DOM`)
                elements.forEach((el, i) => {
                    console.log(`Element ${i}:`, el, 'Styles:', el.style.cssText, 'Classes:', el.className)
                })
                
                // Also check for any CodeMirror line elements
                const cmLines = document.querySelectorAll('.cm-line')
                console.log(`📝 Found ${cmLines.length} .cm-line elements`)
                if (cmLines.length > 0) {
                    console.log('First 3 lines:', Array.from(cmLines).slice(0, 3))
                }
            }, 500)
            
            // Test clearing after 5 seconds
            setTimeout(() => {
                console.log('🧹 Clearing test indicators')
                clearCodeAnalysisLineIndicators()
            }, 5000)
        }
        
        // Make test functions available globally for debugging
        window.testLineIndicators = testLineIndicators
        window.testVisibleIndicator = testVisibleIndicator

        return {
            code,
            output,
            selectedLanguage,
            extensions,
            view,
            isReadOnly,
            roomId,
            currentUserId,
            currentProblem,
            computedExtensions,
            socket,
            handleReady,
            handleCodeChange,
            updateLanguage,
            onProblemChanged,
            auth,
            // Code analysis
            showCodeAnalysis,
            currentCodeBlock,
            onHighlightLine,
            onApplyFix,
            onExplainIssue,
            onCodeAnalysisDismissed,
            onIssuesFound,
            // Code analysis line indicators
            showCodeAnalysisLineIndicators,
            clearCodeAnalysisLineIndicators,
            updateCodeAnalysisLineIndicators,
            // Scaffolding notification
            showScaffoldingNotification,
            scaffoldingNotificationText,
            // Chat handling
            handleCodeRunnerChatMessage,
            pairChat,
            // Test function
            testLineIndicators,
            testVisibleIndicator,
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
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
    background: white;
    border: 1px solid #e2e8f0;
}

.main-content {
    flex: 1;
    display: flex;
    gap: 1rem;
    padding: 1rem;
    min-height: 0;
}

.left-panel {
    width: 350px;
    flex-shrink: 0;
}

.center-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
}

.right-panel {
    width: 500px;
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

/* Remote selection styling - simplified for pair programming */
[class*="remote-selection-"] {
    border-radius: 3px;
    border: 1px solid rgba(0, 0, 0, 0.2);
    backdrop-filter: blur(1px);
}

/* Two-user selection colors for pair programming */
.remote-selection-me { 
    background-color: rgba(79, 70, 229, 0.3) !important; 
    border-color: rgba(79, 70, 229, 0.5); 
}
.remote-selection-other { 
    background-color: rgba(239, 68, 68, 0.3) !important; 
    border-color: rgba(239, 68, 68, 0.5); 
}

/* Dynamic user-specific selections based on socket ID hash */
:deep(.cm-editor) [class*="remote-selection-"] {
    position: relative;
    z-index: 1;
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

/* Small Scaffolding Notification */
.scaffolding-notification {
    position: fixed;
    top: 20px;
    right: 20px;
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    padding: 12px 16px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    z-index: 1000;
    max-width: 300px;
    animation: slideInRight 0.3s ease-out;
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

/* Code Analysis Line Indicators */
.code-analysis-line-indicator {
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
}

.code-analysis-line-indicator.severity-high {
    background: #dc3545;
    box-shadow: 0 0 4px rgba(220, 53, 69, 0.4);
}

.code-analysis-line-indicator.severity-medium {
    background: #ffc107;
    box-shadow: 0 0 4px rgba(255, 193, 7, 0.4);
}

.code-analysis-line-indicator.severity-low {
    background: #28a745;
    box-shadow: 0 0 4px rgba(40, 167, 69, 0.4);
}

/* Hover effect for better visibility */
.cm-editor:hover .code-analysis-line-indicator {
    opacity: 1;
}

/* Animation for when indicators appear */
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

.code-analysis-line-indicator {
    animation: codeAnalysisSlideIn 0.3s ease-out;
}

/* Code Analysis Line Decorations - Global styles for CodeMirror */
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

/* Analyzing state - more subtle, animated */
:global(.code-analysis-line-mark.analyzing) {
    border-left: 3px solid #6c757d !important;
    opacity: 0.6;
    animation: analysisIndicatorPulse 2s ease-in-out infinite;
}

@keyframes analysisIndicatorPulse {
    0%, 100% { opacity: 0.6; }
    50% { opacity: 0.9; }
}
</style>
