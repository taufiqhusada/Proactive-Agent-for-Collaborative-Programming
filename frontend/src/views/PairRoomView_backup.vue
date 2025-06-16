<template>
    <div class="container">
        <div class="row">
            <div class="col mt-3">
                <div class="form-group">
                    <select id="languageSelect" class="form-select" v-model="selectedLanguage" @change="updateLanguage">
                        <option value="python">Python</option>
                        <option value="java">Java</option>
                        <option value="cpp">C++</option>
                        <option value="javascript">JavaScript</option>
                    </select>
                    <div class="form-check mt-2">
                        <input class="form-check-input" type="checkbox" v-model="isReadOnly" id="readOnlyMode">
                        <label class="form-check-label" for="readOnlyMode">
                            Read-only Mode
                        </label>
                    </div>
                    <!-- Debug button for testing decorations -->
                    <button class="btn btn-sm btn-secondary mt-2" @click="testDecoration">
                        Test Highlighting
                    </button>
                </div>

                <codemirror v-model="code" 
                    :style="{ height: '78vh' }" 
                    :autofocus="!isReadOnly"
                    :indent-with-tab="true"
                    style="max-width:36rem; font-size: smaller;" 
                    :tab-size="2" 
                    :extensions="computedExtensions"
                    @ready="handleReady" 
                    @update:value="handleCodeChange" 
                    @focus="log('focus', $event)"
                    @blur="log('blur', $event)" />
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
import { oneDark } from '@codemirror/theme-one-dark'
import { EditorState, StateField, StateEffect } from '@codemirror/state'
import { EditorView, Decoration, WidgetType } from '@codemirror/view'
import { useRoute } from 'vue-router'
import { useSocket } from '@/lib/socket'
import { debounce } from 'lodash'

export default defineComponent({
    components: {
        Codemirror,
    },

    setup() {
        const route = useRoute()
        const roomId = String(route.params.roomId)
        const code = ref('print("Hello")')
        const output = ref('')
        const selectedLanguage = ref('python')
        const extensions = ref([python(), oneDark])
        const view = shallowRef()
        const lastReceivedContent = ref('')
        const isReadOnly = ref(false)
        const isLocalUpdate = ref(false)
        const { socket, connect } = useSocket()

        const languages = {
            python: python(),
            java: java(),
            cpp: cpp(),
            javascript: javascript(),
        }

        // Simple reactive store for remote cursors
        const remoteCursors = ref(new Map())
        
        // Function to create decorations from remote cursors
        const createRemoteCursorDecorations = (state) => {
            const decorations = []
            for (const [userId, cursorData] of remoteCursors.value) {
                const { from, to, color } = cursorData
                
                // Ensure from and to are valid numbers and within document bounds
                const docLength = state.doc.length
                const validFrom = Math.max(0, Math.min(from, to, docLength))
                const validTo = Math.max(validFrom, Math.min(Math.max(from, to), docLength))
                
                // Add selection decoration if there's a range
                if (validTo > validFrom) {
                    decorations.push(
                        Decoration.mark({
                            class: `remote-selection-${userId}`,
                            style: `background-color: ${color}; opacity: 0.4;`
                        }).range(validFrom, validTo)
                    )
                }
                
                // Add cursor decoration at the cursor position
                decorations.push(
                    Decoration.widget({
                        widget: new RemoteCursorWidget(userId, color),
                        side: 1
                    }).range(validTo)
                )
            }
            return Decoration.set(decorations)
        }
        
        // Remote cursor widget for showing cursor indicators
        class RemoteCursorWidget extends WidgetType {
            constructor(userId, color) {
                super()
                this.userId = userId
                this.color = color
            }
            
            toDOM() {
                const cursor = document.createElement('span')
                cursor.className = `remote-cursor remote-cursor-${this.userId}`
                cursor.style.cssText = `
                    position: absolute;
                    width: 2px;
                    height: 1.2em;
                    background-color: ${this.color};
                    pointer-events: none;
                    z-index: 100;
                `
                return cursor
            }
        }
        
        // Computed property for extensions that includes readonly state and remote cursors
        const computedExtensions = computed(() => {
            const langExtension = languages[selectedLanguage.value]
            // Create a reactive decoration provider that updates when remoteCursors changes
            const remoteCursorExtension = EditorView.decorations.of((state) => {
                // This will be called whenever the editor view updates
                return createRemoteCursorDecorations(state)
            })
            
            const baseExtensions = [langExtension, oneDark, remoteCursorExtension, selectionUpdateExtension]
            if (isReadOnly.value) {
                baseExtensions.push(EditorState.readOnly.of(true))
                baseExtensions.push(EditorView.editable.of(false))
            }
            // Add the current remoteCursors value as a dependency so extensions recompute when it changes
            baseExtensions.push(EditorView.decorations.of(() => createRemoteCursorDecorations(view.value?.state)))
            return baseExtensions
        })

        const handleReady = (payload) => {
            view.value = payload.view
        }

        const execute = async () => {
            const res = await runCode(code.value)
            output.value = res.stderr || res.stdout || 'no output'
        }

        // Test function to manually trigger decorations
        const testDecoration = () => {
            if (view.value) {
                console.log('Testing decoration manually')
                const testUserId = 'test-user-123'
                const testColor = '#ff6b6b'
                
                // Add a test cursor/selection
                remoteCursors.value.set(testUserId, {
                    from: 0,
                    to: 5,
                    color: testColor
                })
                
                // Trigger a view update to show the decorations
                view.value.dispatch({ effects: [] })
                
                // Remove it after 3 seconds
                setTimeout(() => {
                    remoteCursors.value.delete(testUserId)
                    if (view.value) {
                        view.value.dispatch({ effects: [] })
                    }
                }, 3000)
            }
        }

        // Generate random color for user
        const generateUserColor = (userId) => {
            const colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7', '#dda0dd', '#98d8c8']
            const hash = userId.split('').reduce((a, b) => {
                a = ((a << 5) - a) + b.charCodeAt(0)
                return a & a
            }, 0)
            return colors[Math.abs(hash) % colors.length]
        }

        // Broadcast current selection to other users
        const broadcastSelection = debounce(() => {
            if (view.value && !isReadOnly.value) {
                const selection = view.value.state.selection.main
                if (selection.from !== selection.to) { // Only broadcast if there's an actual selection
                    console.log('Broadcasting selection:', selection.from, 'to', selection.to)
                    socket.emit('selection', {
                        room: roomId,
                        userId: socket.id,
                        from: selection.from,
                        to: selection.to,
                        color: generateUserColor(socket.id)
                    })
                } else {
                    // Clear selection if no text is selected
                    socket.emit('selection', {
                        room: roomId,
                        userId: socket.id,
                        from: 0,
                        to: 0,
                        color: generateUserColor(socket.id)
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
                    // Update the remote cursors Map
                    if (data.from !== data.to && 
                        typeof data.from === 'number' && 
                        typeof data.to === 'number' && 
                        data.from >= 0 && 
                        data.to >= 0) {
                        
                        console.log('Adding remote selection decoration from', data.from, 'to', data.to)
                        remoteCursors.value.set(data.userId, {
                            from: data.from,
                            to: data.to,
                            color: data.color || generateUserColor(data.userId)
                        })
                    } else {
                        console.log('Clearing remote selection (no valid selection)')
                        remoteCursors.value.delete(data.userId)
                    }
                    
                    // Trigger a view update to refresh decorations
                    view.value.dispatch({ effects: [] })
                } catch (error) {
                    console.error('Error handling remote selection:', error)
                }
            } else {
                console.log('Ignoring selection from same user or no view')
            }
        }

        const debouncedBroadcast = debounce((newValue) => {
            if (!isReadOnly.value) {
                console.log('Broadcasting update:', newValue)
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

        onMounted(() => {
            connect()
            
            // Wait for connection before joining room
            socket.on('connect', () => {
                console.log('Connected to server, joining room:', roomId)
                socket.emit('join', { room: roomId }, (response) => {
                    if (response && response.code) {
                        console.log('Received initial code:', response.code)
                        lastReceivedContent.value = response.code
                        isLocalUpdate.value = true
                        code.value = response.code
                    }
                })
            })

            socket.on('update', ({ delta, sourceId }) => {
                if (sourceId !== socket.id) {
                    console.log('Received update:', delta)
                    lastReceivedContent.value = delta
                    isLocalUpdate.value = true
                    code.value = delta
                }
            })

            socket.on('selection', (data) => {
                console.log('Received selection:', data)
                handleRemoteSelection(data)
            })
            
            // Handle user disconnections to clear their cursors
            socket.on('user_disconnected', (data) => {
                console.log('User disconnected:', data.userId)
                remoteCursors.value.delete(data.userId)
                if (view.value) {
                    view.value.dispatch({ effects: [] })
                }
            })

            socket.on('connect_error', (error) => {
                console.error('Socket connection error:', error)
            })

            return () => {
                socket.off('connect')
                socket.off('update')
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
            extensions,
            computedExtensions,
            handleReady,
            updateLanguage,
            execute,
            handleCodeChange,
            isReadOnly,
            testDecoration,
            log: console.log
        }
    }
})
</script>

<style>
.form-select {
    max-width: 25%;
}

/* Remote selection styling - make sure these are visible */
[class*="remote-selection-"] {
    border-radius: 2px;
    transition: background-color 0.2s ease;
    padding: 1px 0;
}

/* Fallback styles for different user IDs */
.remote-selection-1 { background-color: rgba(255, 107, 107, 0.3) !important; }
.remote-selection-2 { background-color: rgba(78, 205, 196, 0.3) !important; }
.remote-selection-3 { background-color: rgba(69, 183, 209, 0.3) !important; }
.remote-selection-4 { background-color: rgba(150, 206, 180, 0.3) !important; }
.remote-selection-5 { background-color: rgba(255, 234, 167, 0.3) !important; }
.remote-selection-6 { background-color: rgba(221, 160, 221, 0.3) !important; }
.remote-selection-7 { background-color: rgba(152, 216, 200, 0.3) !important; }

/* Ensure CodeMirror content is visible */
.cm-editor .cm-content {
    position: relative;
}
</style>
