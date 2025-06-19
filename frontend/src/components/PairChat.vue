<template>
    <div class="pair-chat">
        <div class="chat-header">
            <h6 class="chat-title">
                <span class="chat-icon">💬</span>
                Team Chat
            </h6>
            <div class="online-users">
                <span class="user-count">{{ onlineUsers }} online</span>
            </div>
        </div>

        <div class="chat-messages" ref="messagesContainer">
            <div v-for="message in messages" :key="message.id" class="message-wrapper">
                <div 
                    :class="[
                        'message', 
                        { 
                            'own-message': message.userId === currentUserId,
                            'ai-message': message.isAI,
                            'system-message': message.isSystem
                        }
                    ]"
                >
                    <div class="message-header">
                        <span class="username">
                            <span v-if="message.isAI" class="ai-badge">🤖</span>
                            {{ message.username }}
                        </span>
                        <span class="timestamp">{{ formatTime(message.timestamp) }}</span>
                    </div>
                    <div class="message-content">{{ message.content }}</div>
                </div>
            </div>
            <div v-if="messages.length === 0" class="empty-chat">
                <span class="empty-text">Start chatting with your teammate!</span>
            </div>
        </div>

        <div class="chat-input">
            <div class="input-wrapper">
                <input 
                    v-model="newMessage" 
                    @keyup.enter="sendMessage"
                    placeholder="Type your message..."
                    class="message-input"
                    :disabled="!isConnected"
                />
                <button 
                    @click="toggleAutoRecording" 
                    :class="['auto-record-button', { active: autoRecordingEnabled }]"
                    :disabled="!isConnected || !speechSupported"
                    :title="speechSupported ? (autoRecordingEnabled ? 'Auto-recording active - Click to pause' : 'Enable auto-recording') : 'Speech recognition not supported'"
                    ref="autoRecordButton"
                >
                    <svg v-if="!autoRecordingEnabled" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <polygon points="10,8 16,12 10,16"/>
                    </svg>
                    <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="6" y="4" width="4" height="16"/>
                        <rect x="14" y="4" width="4" height="16"/>
                    </svg>
                    <!-- Invitation tooltip -->
                    <div v-if="showInviteTooltip && speechSupported && !autoRecordingEnabled" class="invite-tooltip">
                        <div class="tooltip-content">
                            <span class="tooltip-text">✨ Try voice chat!</span>
                            <button @click.stop="dismissTooltip" class="tooltip-close">×</button>
                        </div>
                        <div class="tooltip-arrow"></div>
                    </div>
                </button>
                <button 
                    @click="toggleAIVoice" 
                    :class="['ai-voice-button', { active: aiVoiceEnabled, speaking: isSpeaking }]"
                    :disabled="!isConnected || !ttsSupported"
                    :title="ttsSupported ? (aiVoiceEnabled ? 'AI voice enabled - Click to mute' : 'AI voice muted - Click to enable') : 'Text-to-speech not supported'"
                >
                    <svg v-if="aiVoiceEnabled && !isSpeaking" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 5L6 9H2v6h4l5 4V5z"/>
                        <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/>
                    </svg>
                    <svg v-else-if="!aiVoiceEnabled" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 5L6 9H2v6h4l5 4V5z"/>
                        <line x1="23" y1="9" x2="17" y2="15"/>
                        <line x1="17" y1="9" x2="23" y2="15"/>
                    </svg>
                    <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 5L6 9H2v6h4l5 4V5z"/>
                        <circle cx="19" cy="12" r="3"/>
                    </svg>
                </button>
                <button 
                    @click="sendMessage" 
                    class="send-button"
                    :disabled="!newMessage.trim() || !isConnected"
                >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="22" y1="2" x2="11" y2="13"/>
                        <polygon points="22,2 15,22 11,13 2,9 22,2"/>
                    </svg>
                </button>
            </div>
            <div v-if="autoRecordingEnabled" class="voice-feedback">
                <div v-if="!isSpeaking" class="listening-indicator">
                    <span class="mic-icon">🎤</span>
                    <span class="listening-text">Auto-recording active</span>
                </div>
                <div v-if="isSpeaking" class="ai-speaking-indicator">
                    <span class="ai-icon">🤖</span>
                    <span class="ai-text">CodeBot speaking (recording paused)</span>
                </div>
                <div v-if="currentAutoTranscript && autoRecordingEnabled && !isSpeaking" class="auto-transcript">
                    <strong>Voice:</strong> "{{ currentAutoTranscript }}"
                </div>
                <div v-if="isProcessingSpeech" class="processing-indicator">
                    <span class="processing-text">Processing speech...</span>
                </div>
                <div v-if="speechQueue.length > 0" class="queue-indicator">
                    <span class="queue-text">{{ speechQueue.length }} message(s) in queue</span>
                </div>
            </div>
            <div v-if="!speechSupported && showSpeechWarning" class="speech-warning">
                Speech recognition is not supported in this browser
            </div>
        </div>
    </div>
</template>

<script>
import { defineComponent, ref, onMounted, onUnmounted, nextTick } from 'vue'

export default defineComponent({
    name: 'PairChat',
    props: {
        socket: {
            type: Object,
            required: true
        },
        roomId: {
            type: String,
            required: true
        },
        currentUserId: {
            type: String,
            required: true
        },
        username: {
            type: String,
            default: 'Guest'
        }
    },
    setup(props) {
        const messages = ref([])
        const newMessage = ref('')
        const messagesContainer = ref(null)
        const isConnected = ref(false)
        const onlineUsers = ref(1)
        
        // Voice input state
        const speechSupported = ref(false)
        const showSpeechWarning = ref(false)
        const autoRecordingEnabled = ref(false)
        const isProcessingSpeech = ref(false)
        const speechQueue = ref([])
        const lastSpeechTime = ref(0)
        const currentAutoTranscript = ref('')
        const showInviteTooltip = ref(false)
        let autoRecognition = null
        let speechProcessor = null

        // Text-to-Speech state
        const ttsSupported = ref(false)
        const isSpeaking = ref(false)
        const aiVoiceEnabled = ref(true) // Can be toggled by user
        let currentUtterance = null

        const formatTime = (timestamp) => {
            const date = new Date(timestamp)
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }

        const scrollToBottom = () => {
            nextTick(() => {
                if (messagesContainer.value) {
                    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
                }
            })
        }

        const sendMessage = () => {
            if (!newMessage.value.trim() || !props.socket) return

            const message = {
                id: Date.now(),
                content: newMessage.value.trim(),
                userId: props.currentUserId,
                username: props.username,
                timestamp: new Date().toISOString(),
                room: props.roomId
            }

            // Add to local messages immediately
            messages.value.push(message)
            
            console.log('Sending message via socket:', message)
            console.log('Socket connected:', props.socket.connected)
            console.log('Socket namespace:', props.socket.nsp)
            
            // Send to socket - make sure we're using the right namespace
            props.socket.emit('chat_message', message)
            
            newMessage.value = ''
            scrollToBottom()
        }

        const handleIncomingMessage = (message) => {
            // Don't add our own messages again
            if (message.userId === props.currentUserId) return
            
            messages.value.push(message)
            
            // Don't use browser TTS for AI messages with hasAudio flag
            // The audio will come separately via ai_speech event
            if (message.isAI && !message.hasAudio && aiVoiceEnabled.value) {
                // Fallback to browser TTS only if no server audio is available
                speakMessage(message.content, true)
            }
            
            scrollToBottom()
        }

        const handleAISpeech = (data) => {
            // Play high-quality AI speech audio
            if (aiVoiceEnabled.value && data.audioData) {
                playAudioFromBase64(data.audioData)
            }
        }

        const handleUserJoined = (data) => {
            // Update user count from server data
            if (data.userCount !== undefined) {
                onlineUsers.value = data.userCount
            }
            
            // Add system message
            messages.value.push({
                id: Date.now(),
                content: `${props.username || 'Someone'} joined the room`,
                userId: 'system',
                username: 'System',
                timestamp: new Date().toISOString(),
                isSystem: true
            })
            scrollToBottom()
        }

        const handleUserLeft = (data) => {
            // Update user count from server data
            if (data.userCount !== undefined) {
                onlineUsers.value = data.userCount
            }
            
            // Add system message
            messages.value.push({
                id: Date.now(),
                content: `${props.username || 'Someone'} left the room`,
                userId: 'system',
                username: 'System',
                timestamp: new Date().toISOString(),
                isSystem: true
            })
            scrollToBottom()
        }

        const handleUserCountUpdate = (data) => {
            // Handle explicit user count updates from server
            if (data.userCount !== undefined) {
                onlineUsers.value = data.userCount
                console.log('User count updated to:', data.userCount)
            }
        }

        // Voice input functions
        const initSpeechRecognition = () => {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
            
            if (SpeechRecognition) {
                speechSupported.value = true
                
                // Initialize auto recognition (for continuous listening)
                autoRecognition = new SpeechRecognition()
                setupRecognition(autoRecognition, true)
                
                // Initialize speech processor for queue management
                initSpeechProcessor()
                
                // Start auto recording if enabled
                if (autoRecordingEnabled.value) {
                    startAutoRecording()
                }
            } else {
                speechSupported.value = false
                showSpeechWarning.value = true
                console.log('Speech recognition not supported')
            }
        }

        const setupRecognition = (recognitionInstance, isAutoMode) => {
            recognitionInstance.continuous = true
            recognitionInstance.interimResults = true
            recognitionInstance.lang = 'en-US'
            recognitionInstance.maxAlternatives = 1
            
            let finalTranscript = ''
            let silenceTimer = null
            let isActive = false
            
            recognitionInstance.onstart = () => {
                console.log('Auto recognition started')
                isActive = true
            }
            
            recognitionInstance.onresult = (event) => {
                let interimTranscript = ''
                
                // Clear existing silence timer
                if (silenceTimer) {
                    clearTimeout(silenceTimer)
                    silenceTimer = null
                }
                
                // Process results
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript
                    if (event.results[i].isFinal) {
                        finalTranscript += transcript + ' '
                    } else {
                        interimTranscript += transcript
                    }
                }
                
                const currentTranscript = (finalTranscript + interimTranscript).trim()
                
                // For auto mode, queue the speech with timestamp
                if (currentTranscript) {
                    lastSpeechTime.value = Date.now()
                    
                    // Update the current auto transcript for display
                    currentAutoTranscript.value = currentTranscript
                    
                    // Set silence timer for auto mode
                    silenceTimer = setTimeout(() => {
                        if (finalTranscript.trim()) {
                            queueSpeechForProcessing(finalTranscript.trim(), Date.now())
                            finalTranscript = ''
                            // Clear the auto transcript after queuing
                            setTimeout(() => {
                                currentAutoTranscript.value = ''
                            }, 1000)
                        }
                    }, 1000) // 1 second for auto mode
                }
            }
            
            recognitionInstance.onend = () => {
                isActive = false
                if (silenceTimer) {
                    clearTimeout(silenceTimer)
                    silenceTimer = null
                }
                
                console.log('Auto recognition ended')
                // Restart auto recognition if it's enabled
                if (autoRecordingEnabled.value) {
                    setTimeout(() => {
                        if (autoRecordingEnabled.value && !isActive) {
                            try {
                                recognitionInstance.start()
                            } catch (error) {
                                console.log('Auto restart failed, retrying...', error)
                                setTimeout(() => {
                                    if (autoRecordingEnabled.value) {
                                        startAutoRecording()
                                    }
                                }, 1000)
                            }
                        }
                    }, 100)
                }
            }
            
            recognitionInstance.onerror = (event) => {
                console.error(`${isAutoMode ? 'Auto' : 'Manual'} speech recognition error:`, event.error)
                
                if (silenceTimer) {
                    clearTimeout(silenceTimer)
                    silenceTimer = null
                }
                
                // Error handled for auto mode only now
                
                if (event.error === 'not-allowed') {
                    alert('Please allow microphone access to use voice input')
                    autoRecordingEnabled.value = false
                } else if (event.error === 'no-speech') {
                    console.log(`${isAutoMode ? 'Auto' : 'Manual'} - No speech detected`)
                } else if (event.error === 'aborted') {
                    console.log(`${isAutoMode ? 'Auto' : 'Manual'} - Speech recognition aborted`)
                } else {
                    // Handle other errors for auto mode
                    showSpeechWarning.value = true
                    setTimeout(() => {
                        showSpeechWarning.value = false
                    }, 3000)
                    
                    // Restart auto recognition on error if enabled
                    if (isAutoMode && autoRecordingEnabled.value) {
                        setTimeout(() => {
                            if (autoRecordingEnabled.value) {
                                startAutoRecording()
                            }
                        }, 2000)
                    }
                }
            }
        }

        const initSpeechProcessor = () => {
            speechProcessor = setInterval(() => {
                processSpeechQueue()
            }, 500) // Process queue every 500ms
        }

        const queueSpeechForProcessing = (transcript, timestamp) => {
            const speechItem = {
                id: Date.now() + Math.random(),
                transcript: transcript,
                timestamp: timestamp,
                userId: props.currentUserId
            }
            
            speechQueue.value.push(speechItem)
            console.log('Queued speech:', transcript, 'Queue length:', speechQueue.value.length)
        }

        const processSpeechQueue = () => {
            if (speechQueue.value.length === 0 || isProcessingSpeech.value) return
            
            const now = Date.now()
            const readyItems = speechQueue.value.filter(item => 
                now - item.timestamp > 100 // Wait 100ms before processing
            )
            
            if (readyItems.length === 0) return
            
            isProcessingSpeech.value = true
            
            // Group speech items by user and time (within 3 seconds)
            const groups = groupSpeechByUserAndTime(readyItems, 3000)
            
            groups.forEach(group => {
                // All items in a group are from the same user within the time window
                const userId = group[0].userId
                const mergedTranscript = group.map(item => item.transcript).join(' ')
                sendAutoMessage(mergedTranscript, userId)
                
                // Remove processed items from queue
                group.forEach(item => {
                    const index = speechQueue.value.findIndex(qItem => qItem.id === item.id)
                    if (index > -1) {
                        speechQueue.value.splice(index, 1)
                    }
                })
            })
            
            setTimeout(() => {
                isProcessingSpeech.value = false
            }, 300)
        }

        const groupSpeechByTime = (items, maxGapMs) => {
            if (items.length === 0) return []
            
            // Sort by timestamp
            const sorted = [...items].sort((a, b) => a.timestamp - b.timestamp)
            const groups = []
            let currentGroup = [sorted[0]]
            
            for (let i = 1; i < sorted.length; i++) {
                const gap = sorted[i].timestamp - sorted[i-1].timestamp
                if (gap <= maxGapMs) {
                    currentGroup.push(sorted[i])
                } else {
                    groups.push(currentGroup)
                    currentGroup = [sorted[i]]
                }
            }
            groups.push(currentGroup)
            
            return groups
        }

        const groupSpeechByUserAndTime = (items, maxGapMs) => {
            if (items.length === 0) return []
            
            // Sort by timestamp
            const sorted = [...items].sort((a, b) => a.timestamp - b.timestamp)
            const groups = []
            let currentGroup = [sorted[0]]
            
            for (let i = 1; i < sorted.length; i++) {
                const gap = sorted[i].timestamp - sorted[i-1].timestamp
                const sameUser = sorted[i].userId === sorted[i-1].userId
                
                // Group if same user AND within time gap
                if (sameUser && gap <= maxGapMs) {
                    currentGroup.push(sorted[i])
                } else {
                    groups.push(currentGroup)
                    currentGroup = [sorted[i]]
                }
            }
            groups.push(currentGroup)
            
            return groups
        }

        const sendAutoMessage = (transcript, userId) => {
            if (!transcript.trim()) return
            
            // CRITICAL: Don't send voice messages while AI is speaking to prevent feedback
            if (isSpeaking.value) {
                console.log('🚫 Blocked voice message while AI is speaking:', transcript)
                return
            }
            
            const message = {
                id: Date.now() + Math.random(),
                content: transcript.trim(),
                userId: userId,
                username: props.username, // Always use the current user's name for auto-generated messages
                timestamp: new Date().toISOString(),
                room: props.roomId,
                isAutoGenerated: true
            }
            
            // Add to local messages
            messages.value.push(message)
            
            // Send via socket
            if (props.socket) {
                props.socket.emit('chat_message', message)
            }
            
            scrollToBottom()
            console.log('Auto-sent message:', transcript)
        }

        const toggleAutoRecording = () => {
            if (!speechSupported.value) return
            
            autoRecordingEnabled.value = !autoRecordingEnabled.value
            
            if (autoRecordingEnabled.value) {
                startAutoRecording()
                console.log('Auto recording enabled')
                // Hide the tooltip when user starts using the feature
                showInviteTooltip.value = false
            } else {
                stopAutoRecording()
                console.log('Auto recording disabled')
            }
        }

        const dismissTooltip = () => {
            showInviteTooltip.value = false
            // Store in localStorage to prevent showing again for this session
            localStorage.setItem('voiceChatTooltipDismissed', 'true')
        }

        const startAutoRecording = () => {
            if (!autoRecognition || !speechSupported.value) return
            
            try {
                autoRecognition.start()
                console.log('Auto recording started')
            } catch (error) {
                console.error('Error starting auto recording:', error)
                // If already running, that's okay
                if (error.name !== 'InvalidStateError') {
                    autoRecordingEnabled.value = false
                }
            }
        }

        const stopAutoRecording = () => {
            if (autoRecognition) {
                try {
                    autoRecognition.stop()
                    console.log('Auto recording stopped')
                } catch (error) {
                    console.error('Error stopping auto recording:', error)
                }
            }
        }

        const stopVoiceInput = () => {
            if (autoRecognition) {
                try {
                    autoRecognition.stop()
                } catch (error) {
                    console.error('Error stopping voice input:', error)
                }
            }
        }

        // Text-to-Speech functions (OpenAI TTS)
        const initTextToSpeech = () => {
            // Check if Web Audio API is supported for high-quality audio playback
            if ('AudioContext' in window || 'webkitAudioContext' in window) {
                ttsSupported.value = true
                console.log('High-quality audio playback supported')
            } else {
                ttsSupported.value = false
                console.log('High-quality audio playback not supported')
            }
        }

        const playAudioFromBase64 = async (base64Audio) => {
            if (!ttsSupported.value || !aiVoiceEnabled.value) return
            
            try {
                // Stop any current speech
                stopSpeaking()
                
                // CRITICAL: Pause voice recording while AI is speaking to prevent feedback loop
                const wasAutoRecordingActive = autoRecordingEnabled.value
                if (wasAutoRecordingActive) {
                    console.log('🔇 Temporarily pausing voice recording to prevent AI feedback')
                    stopAutoRecording()
                }
                
                // Convert base64 to blob
                const audioBytes = atob(base64Audio)
                const audioArray = new Uint8Array(audioBytes.length)
                for (let i = 0; i < audioBytes.length; i++) {
                    audioArray[i] = audioBytes.charCodeAt(i)
                }
                
                const audioBlob = new Blob([audioArray], { type: 'audio/mpeg' })
                const audioUrl = URL.createObjectURL(audioBlob)
                
                // Create and play audio element
                const audio = new Audio(audioUrl)
                audio.volume = 0.8
                
                audio.onloadstart = () => {
                    isSpeaking.value = true
                    console.log('🔊 Started playing AI speech (voice recording paused)')
                }
                
                audio.onended = () => {
                    isSpeaking.value = false
                    currentUtterance = null
                    URL.revokeObjectURL(audioUrl)
                    console.log('✅ Finished playing AI speech')
                    
                    // Resume voice recording after AI finishes speaking (with delay)
                    if (wasAutoRecordingActive) {
                        setTimeout(() => {
                            console.log('🎤 Resuming voice recording after AI speech')
                            startAutoRecording()
                        }, 500) // 500ms delay to ensure audio has fully stopped
                    }
                }
                
                audio.onerror = (error) => {
                    console.error('Audio playback error:', error)
                    isSpeaking.value = false
                    currentUtterance = null
                    URL.revokeObjectURL(audioUrl)
                    
                    // Resume voice recording even if audio failed
                    if (wasAutoRecordingActive) {
                        setTimeout(() => {
                            console.log('🎤 Resuming voice recording after AI audio error')
                            startAutoRecording()
                        }, 500)
                    }
                }
                
                currentUtterance = audio
                await audio.play()
                
            } catch (error) {
                console.error('Error playing audio:', error)
                isSpeaking.value = false
                currentUtterance = null
            }
        }

        const speakMessage = async (text, isAI = false) => {
            // This function is now mainly for fallback or non-AI messages
            // AI messages will use the high-quality audio from the server
            if (!isAI) {
                // For non-AI messages, we can still use browser TTS if needed
                if ('speechSynthesis' in window && text.trim()) {
                    const utterance = new SpeechSynthesisUtterance(text)
                    utterance.rate = 1.0
                    utterance.pitch = 1.0
                    utterance.volume = 0.6
                    speechSynthesis.speak(utterance)
                }
            }
            // AI messages will be handled by playAudioFromBase64
        }

        const stopSpeaking = () => {
            if (speechSynthesis.speaking) {
                speechSynthesis.cancel()
                isSpeaking.value = false
                currentUtterance = null
            }
        }

        const toggleAIVoice = () => {
            aiVoiceEnabled.value = !aiVoiceEnabled.value
            if (!aiVoiceEnabled.value) {
                stopSpeaking()
            }
            console.log('AI voice', aiVoiceEnabled.value ? 'enabled' : 'disabled')
        }

        onMounted(() => {
            console.log('PairChat mounted with socket:', props.socket)
            console.log('Socket connected:', props.socket?.connected)
            console.log('Room ID:', props.roomId)
            console.log('Current User ID:', props.currentUserId)
            
            // Initialize speech recognition
            initSpeechRecognition()
            
            // Initialize text-to-speech
            initTextToSpeech()
            
            // Show invitation tooltip immediately if not previously dismissed
            setTimeout(() => {
                const dismissed = localStorage.getItem('voiceChatTooltipDismissed')
                if (!dismissed && speechSupported.value && !autoRecordingEnabled.value) {
                    showInviteTooltip.value = true
                    
                    // Auto-hide after 8 seconds
                    setTimeout(() => {
                        showInviteTooltip.value = false
                    }, 8000)
                }
            }, 500) // Show after just 500ms of component being mounted
            
            if (props.socket) {
                isConnected.value = props.socket.connected

                props.socket.on('connect', () => {
                    console.log('Socket connected in PairChat')
                    isConnected.value = true
                })

                props.socket.on('disconnect', () => {
                    console.log('Socket disconnected in PairChat')
                    isConnected.value = false
                })

                props.socket.on('chat_message', (data) => {
                    console.log('Received chat message:', data)
                    handleIncomingMessage(data)
                })
                
                props.socket.on('user_joined', (data) => {
                    console.log('User joined:', data)
                    handleUserJoined(data)
                })
                
                props.socket.on('user_left', (data) => {
                    console.log('User left:', data)
                    handleUserLeft(data)
                })

                props.socket.on('user_count_update', (data) => {
                    console.log('User count update:', data)
                    handleUserCountUpdate(data)
                })

                props.socket.on('user_disconnected', (data) => {
                    console.log('User disconnected:', data)
                    handleUserCountUpdate(data)
                })

                props.socket.on('ai_speech', (data) => {
                    console.log('Received AI speech:', data)
                    handleAISpeech(data)
                })
            }
        })

        onUnmounted(() => {
            // Stop all voice input
            stopVoiceInput()
            stopAutoRecording()
            
            // Clear speech processor
            if (speechProcessor) {
                clearInterval(speechProcessor)
            }
            
            if (props.socket) {
                props.socket.off('chat_message', handleIncomingMessage)
                props.socket.off('user_joined', handleUserJoined)
                props.socket.off('user_left', handleUserLeft)
                props.socket.off('user_count_update', handleUserCountUpdate)
                props.socket.off('user_disconnected', handleUserCountUpdate)
                props.socket.off('ai_speech', handleAISpeech)
            }
        })

        return {
            messages,
            newMessage,
            messagesContainer,
            isConnected,
            onlineUsers,
            speechSupported,
            showSpeechWarning,
            autoRecordingEnabled,
            isProcessingSpeech,
            speechQueue,
            currentAutoTranscript,
            showInviteTooltip,
            ttsSupported,
            isSpeaking,
            aiVoiceEnabled,
            formatTime,
            sendMessage,
            toggleAutoRecording,
            toggleAIVoice,
            dismissTooltip
        }
    }
})
</script>

<style scoped>
.pair-chat {
    display: flex;
    flex-direction: column;
    flex: 1;
    background: white;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    overflow: hidden;
    min-height: 0;
}

.chat-header {
    padding: 1rem;
    background: #f8fafc;
    border-bottom: 1px solid #e2e8f0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.chat-title {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    color: #2d3748;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.chat-icon {
    font-size: 1.1rem;
}

.user-count {
    font-size: 0.75rem;
    color: #10b981;
    background: rgba(16, 185, 129, 0.1);
    padding: 0.25rem 0.5rem;
    border-radius: 12px;
    font-weight: 500;
}

.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    min-height: 0;
}

.message-wrapper {
    display: flex;
    flex-direction: column;
}

.message {
    max-width: 80%;
    padding: 0.75rem;
    border-radius: 12px;
    background: #f1f5f9;
    align-self: flex-start;
}

.message.own-message {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    align-self: flex-end;
}

.message.ai-message {
    background: linear-gradient(135deg, #10b981, #059669);
    color: white;
    align-self: flex-start;
    border-left: 4px solid #065f46;
    box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2);
}

.message.system-message {
    background: #f3f4f6;
    color: #6b7280;
    align-self: center;
    max-width: 90%;
    text-align: center;
    font-style: italic;
    border-radius: 16px;
}

.message-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.25rem;
    gap: 0.5rem;
}

.username {
    font-size: 0.75rem;
    font-weight: 600;
    opacity: 0.8;
}

.ai-badge {
    margin-right: 0.25rem;
    font-size: 0.875rem;
}

.timestamp {
    font-size: 0.625rem;
    opacity: 0.6;
}

.message-content {
    font-size: 0.875rem;
    line-height: 1.4;
    word-wrap: break-word;
}

.empty-chat {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #9ca3af;
    font-style: italic;
}

.chat-input {
    padding: 1rem;
    border-top: 1px solid #e2e8f0;
    background: #f8fafc;
}

.input-wrapper {
    display: flex;
    gap: 0.5rem;
    align-items: center;
}

.message-input {
    flex: 1;
    padding: 0.75rem;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    font-size: 0.875rem;
    background: white;
    transition: all 0.2s ease;
}

.message-input:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.message-input:disabled {
    background: #f1f5f9;
    cursor: not-allowed;
}

.send-button {
    padding: 0.75rem;
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
}

.send-button:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.send-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
}

/* Auto-recording button styles */
.auto-record-button {
    position: relative; /* Needed for tooltip positioning */
    padding: 0.75rem;
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #4b5563;
}

.auto-record-button:hover:not(:disabled) {
    background: #f8fafc;
    border-color: #10b981;
    color: #10b981;
}

.auto-record-button.active {
    background: white;
    border-color: #10b981;
    color: #10b981;
    animation: glow 2s ease-in-out infinite alternate;
}

@keyframes glow {
    from {
        box-shadow: 0 0 5px #10b981, 0 0 10px #10b981, 0 0 15px #10b981;
    }
    to {
        box-shadow: 0 0 10px #10b981, 0 0 20px #10b981, 0 0 30px #10b981;
    }
}

.auto-record-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    background: #f1f5f9;
}

/* AI Voice button styles */
.ai-voice-button {
    padding: 0.75rem;
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #4b5563;
}

.ai-voice-button:hover:not(:disabled) {
    background: #f8fafc;
    border-color: #3b82f6;
    color: #3b82f6;
}

.ai-voice-button.active {
    background: white;
    border-color: #3b82f6;
    color: #3b82f6;
}

.ai-voice-button.speaking {
    background: white;
    border-color: #10b981;
    color: #10b981;
    animation: speaking-pulse 1s ease-in-out infinite alternate;
}

@keyframes speaking-pulse {
    from {
        opacity: 0.7;
        transform: scale(1);
    }
    to {
        opacity: 1;
        transform: scale(1.1);
    }
}

.ai-voice-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    background: #f1f5f9;
}

.invite-tooltip {
    position: absolute;
    bottom: 100%;
    right: 0; /* Align to the right edge of the button */
    margin-bottom: 10px;
    z-index: 1000;
    animation: fadeInUp 0.3s ease-out;
}

.tooltip-content {
    background: #1f2937;
    color: white;
    padding: 0.6rem 0.8rem;
    border-radius: 8px;
    font-size: 0.8rem;
    white-space: nowrap;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    display: flex;
    align-items: center;
    gap: 0.5rem;
    max-width: 160px;
}

.tooltip-text {
    flex: 1;
}

.tooltip-close {
    background: none;
    border: none;
    color: white;
    font-size: 1.1rem;
    cursor: pointer;
    padding: 0;
    width: 18px;
    height: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    transition: background-color 0.2s ease;
}

.tooltip-close:hover {
    background: rgba(255, 255, 255, 0.2);
}

.tooltip-arrow {
    position: absolute;
    top: 100%;
    right: 20px; /* Position arrow relative to the right edge */
    width: 0;
    height: 0;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-top: 6px solid #1f2937;
}

@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.voice-feedback {
    margin-top: 0.5rem;
    padding: 0.75rem;
    background: rgba(239, 68, 68, 0.05);
    border: 1px solid rgba(239, 68, 68, 0.2);
    border-radius: 8px;
}

.listening-indicator {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    color: #ef4444;
    font-weight: 500;
    margin-bottom: 0.5rem;
}

.mic-icon {
    font-size: 1rem;
    animation: pulse 1.5s infinite;
}

.listening-text {
    color: #ef4444;
}

.live-transcript {
    font-size: 0.875rem;
    color: #374151;
    font-style: italic;
    padding: 0.5rem;
    background: rgba(255, 255, 255, 0.7);
    border-radius: 4px;
    border-left: 3px solid #ef4444;
    margin-bottom: 0.5rem;
}

.auto-transcript {
    font-size: 0.875rem;
    color: #374151;
    font-style: italic;
    padding: 0.5rem;
    background: rgba(255, 255, 255, 0.7);
    border-radius: 4px;
    border-left: 3px solid #10b981;
    margin-bottom: 0.5rem;
}

.processing-indicator {
    margin-top: 0.5rem;
    font-size: 0.75rem;
    color: #f59e0b;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.processing-text {
    animation: pulse 1s infinite;
}

.queue-indicator {
    margin-top: 0.25rem;
    font-size: 0.75rem;
    color: #6b7280;
    font-weight: 500;
}

.queue-text {
    background: rgba(107, 114, 128, 0.1);
    padding: 0.25rem 0.5rem;
    border-radius: 12px;
}

.speech-warning {
    margin-top: 0.5rem;
    padding: 0.5rem;
    background: rgba(251, 191, 36, 0.1);
    border: 1px solid rgba(251, 191, 36, 0.2);
    border-radius: 6px;
    text-align: center;
    font-size: 0.875rem;
    color: #d97706;
}

@keyframes pulse {
    0%, 100% { 
        opacity: 1; 
        transform: scale(1);
    }
    50% { 
        opacity: 0.8;
        transform: scale(1.05);
    }
}

@keyframes rotate {
    from {
        transform: rotate(0deg);
    }
    to {
        transform: rotate(360deg);
    }
}

/* Scrollbar styling */
.chat-messages::-webkit-scrollbar {
    width: 4px;
}

.chat-messages::-webkit-scrollbar-track {
    background: #f1f5f9;
}

.chat-messages::-webkit-scrollbar-thumb {
    background: #cbd5e1;
    border-radius: 2px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
    background: #94a3b8;
}

.ai-speaking-indicator {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    color: #10b981;
    font-weight: 500;
    margin-bottom: 0.5rem;
}

.ai-icon {
    font-size: 1rem;
    animation: speaking-pulse 1s infinite alternate;
}

.ai-text {
    color: #10b981;
}

@keyframes speaking-pulse {
    from {
        opacity: 0.7;
        transform: scale(1);
    }
    to {
        opacity: 1;
        transform: scale(1.1);
    }
}
</style>
