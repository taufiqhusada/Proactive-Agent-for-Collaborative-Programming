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
                        @update:value="handleCodeChange"
                        class="code-editor" />
                </div>
            </div>

            <!-- Right Panel: Chat -->
            <div class="right-panel">
                <PairChat 
                    :socket="socket" 
                    :room-id="roomId" 
                    :current-user-id="currentUserId" />
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
// import { oneDark } from '@codemirror/theme-one-dark'
// import { basicLight } from '@codemirror/theme-basic-light'
import { EditorState, StateField, StateEffect } from '@codemirror/state'
import { EditorView, Decoration, WidgetType } from '@codemirror/view'
import { useRoute } from 'vue-router'
import { useSocket } from '@/lib/socket'
import { runCode } from '@/lib/runCode'
import { debounce } from 'lodash'
import ProblemDescription from '@/components/ProblemDescription.vue'
import PairChat from '@/components/PairChat.vue'

export default defineComponent({
    components: {
        Codemirror,
        ProblemDescription,
        PairChat,
    },

    setup() {
        const route = useRoute()
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
        const { socket, connect } = useSocket()

        const languages = {
            python: python(),
            java: java(),
            cpp: cpp(),
            javascript: javascript(),
        }

        // Effects for managing remote cursors
        const setRemoteCursor = StateEffect.define()
        const clearRemoteCursor = StateEffect.define()
        
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
                            
                            const isThisUserSelection = className.includes(`remote-selection-${userId}`)
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
                                generateUserColor(userId)
                            
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
                                
                                const isThisUserSelection = className.includes(`remote-selection-${userId}`)
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

        // Computed property for extensions that includes readonly state and remote cursors
        const computedExtensions = computed(() => {
            const langExtension = languages[selectedLanguage.value]
            const baseExtensions = [langExtension, remoteCursorField, selectionUpdateExtension]
            if (isReadOnly.value) {
                baseExtensions.push(EditorState.readOnly.of(true))
                baseExtensions.push(EditorView.editable.of(false))
            }
            return baseExtensions
        })

        const handleReady = (payload) => {
            view.value = payload.view
        }

        const execute = async () => {
            const res = await runCode(code.value)
            output.value = res.stderr || res.stdout || 'no output'
        }

        const onProblemChanged = (data) => {
            console.log('Problem changed:', data.problem.title)
            // You can sync the problem selection across users if needed
            // socket.emit('problem_changed', { room: roomId, problemIndex: data.problemIndex })
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

        // Generate consistent color and class index for user
        const generateUserColor = (userId) => {
            const colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7', '#dda0dd', '#98d8c8']
            const hash = userId.split('').reduce((a, b) => {
                a = ((a << 5) - a) + b.charCodeAt(0)
                return a & a
            }, 0)
            const index = Math.abs(hash) % colors.length
            return {
                color: colors[index],
                classIndex: index
            }
        }

        // Broadcast current selection to other users
        const broadcastSelection = debounce(() => {
            if (view.value && !isReadOnly.value) {
                const selection = view.value.state.selection.main
                const userColor = generateUserColor(socket.id)
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
                            generateUserColor(data.userId)
                        
                        view.value.dispatch({
                            effects: [setRemoteCursor.of({
                                userId: data.userId,
                                from: data.from,
                                to: data.to,
                                color: data.color || generateUserColor(data.userId).color,
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

        // Prevent code changes in readonly mode
        const handleCodeChange = (newValue) => {
            if (isReadOnly.value) {
                // Don't allow changes in readonly mode
                return
            }
            code.value = newValue
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

            socket.on('connect_error', (error) => {
                console.error('Socket connection error:', error)
            })

            return () => {
                socket.off('connect')
                socket.off('update')
                socket.off('cursor')
                socket.off('selection')
                socket.off('user_disconnected')
                socket.off('connect_error')
                socket.emit('leave', { room: roomId })
            }
        })

        return {
            code,
            output,
            selectedLanguage,
            computedExtensions,
            handleReady,
            updateLanguage,
            execute,
            handleCodeChange,
            isReadOnly,
            roomId,
            socket,
            currentUserId,
            onProblemChanged
        }
    }
})
</script>

<style scoped>
.editor-container {
    min-height: 100vh;
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
    width: 300px;
    flex-shrink: 0;
}

.code-editor {
    height: calc(100vh - 120px);
    font-size: 14px;
    line-height: 1.5;
}

/* Remote selection styling - user-specific colors */
[class*="remote-selection-"] {
    border-radius: 3px;
    border: 1px solid rgba(0, 0, 0, 0.2);
    backdrop-filter: blur(1px);
}

/* Individual user selection colors */
.remote-selection-0 { background-color: rgba(255, 107, 107, 0.3) !important; border-color: rgba(255, 107, 107, 0.5); }
.remote-selection-1 { background-color: rgba(78, 205, 196, 0.3) !important; border-color: rgba(78, 205, 196, 0.5); }
.remote-selection-2 { background-color: rgba(69, 183, 209, 0.3) !important; border-color: rgba(69, 183, 209, 0.5); }
.remote-selection-3 { background-color: rgba(150, 206, 180, 0.3) !important; border-color: rgba(150, 206, 180, 0.5); }
.remote-selection-4 { background-color: rgba(255, 234, 167, 0.3) !important; border-color: rgba(255, 234, 167, 0.5); }
.remote-selection-5 { background-color: rgba(221, 160, 221, 0.3) !important; border-color: rgba(221, 160, 221, 0.5); }
.remote-selection-6 { background-color: rgba(152, 216, 200, 0.3) !important; border-color: rgba(152, 216, 200, 0.5); }

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
        height: 400px;
    }
}
</style>
