<template>
    <div class="pair-chat">
        <div class="chat-header">
            <h6 class="chat-title">
                <span class="chat-icon">💬</span>
                Team Chat
            </h6>
            <div class="header-controls">
                <div class="online-users">
                    <span class="user-count">{{ onlineUsers }} online</span>
                </div>
                
                <!-- Session Controls -->
                <div class="session-controls" style="position: relative;">
                    <!-- Start Session Button (shows when session not started) -->
                    <button 
                        v-if="!sessionStarted"
                        @click="startSession" 
                        class="start-session-btn"
                        title="Start Pair Programming Session"
                    >
                        Start Session
                    </button>
                    
                    <!-- Reset Session Button (shows when session started) -->
                    <button 
                        v-else
                        @click="showResetWarning = true" 
                        :disabled="isResetting"
                        class="reset-session-btn"
                        title="Reset Session - Clears all code and conversation"
                    >
                        {{ isResetting ? 'Resetting...' : 'Reset Session' }}
                    </button>
                    
                    <!-- Reset Warning Popup (near button) -->
                    <div v-if="showResetWarning" class="reset-warning-popup">
                        <div class="popup-content">
                            <div class="popup-header">
                                <h4>⚠️ Reset Session?</h4>
                            </div>
                            <div class="popup-body">
                                <p>This will clear all messages and reset AI state.</p>
                            </div>
                            <div class="popup-actions">
                                <button @click="showResetWarning = false" class="cancel-btn-small">
                                    Cancel
                                </button>
                                <button @click="confirmResetSession" class="confirm-btn-small" :disabled="isResetting">
                                    {{ isResetting ? 'Resetting...' : 'Reset' }}
                                </button>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Success Popup (near button) -->
                    <div v-if="showSuccessPopup" class="success-popup-small">
                        <div class="success-content-small">
                            <span class="success-icon">✅</span>
                            <span class="success-text">Reset successful!</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="chat-messages" ref="messagesContainer">
            <div v-for="message in messages" :key="message.id" class="message-wrapper">
                <div 
                    :class="[
                        'message', 
                        { 
                            'own-message': message.userId === currentUserId,
                            'ai-message': message.isAI && !message.isExecutionHelp && !message.isReflection,
                            'ai-reflection-message': message.isAI && message.isReflection,
                            'ai-execution-help': message.isAI && message.isExecutionHelp,
                            'system-message': message.isSystem
                        }
                    ]"
                >
                    <div class="message-header">
                        <span class="username">
                            <span v-if="message.isAI && message.isExecutionHelp" class="ai-badge">🔍</span>
                            <span v-else-if="message.isAI" class="ai-badge">👨‍💻</span>
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
                    @input="handleTypingActivity"
                    :placeholder="sessionStarted ? 'Type your message...' : 'Start session to begin chatting'"
                    class="message-input"
                    :disabled="!isConnected || !sessionStarted"
                />
                <button 
                    @click="toggleAutoRecording" 
                    :class="['auto-record-button', { active: autoRecordingEnabled }]"
                    :disabled="!isConnected || !speechSupported || !sessionStarted"
                    :title="!sessionStarted ? 'Start session to enable voice features' : (speechSupported ? (autoRecordingEnabled ? 'Auto-recording active - Click to pause' : 'Enable auto-recording') : 'Speech recognition not supported')"
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
                    <span class="ai-text">Bob speaking (recording paused)</span>
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
        },
        reflectionSessionId: {
            type: String,
            default: ''
        }
    },
    emits: ['reflection-session-started', 'reflection-session-ended'],
    setup(props, { emit }) {
        const messages = ref([])
        const newMessage = ref('')
        const messagesContainer = ref(null)
        const isConnected = ref(false)
        const onlineUsers = ref(1)
        
        // Voice input state
        const speechSupported = ref(false)
        const speechQueue = ref([])
        const autoRecordingEnabled = ref(false)
        const currentAutoTranscript = ref('')
        const isListening = ref(false)
        const isProcessingSpeech = ref(false)
        const showInviteTooltip = ref(false)
        const showSpeechWarning = ref(false)
        const timerStarted = ref(false) // Flag to track if AI timer was started by sending a message
        const lastSpeechTime = ref(0) // Track when last speech activity occurred
        let autoRecognition = null
        let speechProcessor = null

        // Text-to-Speech state
        const ttsSupported = ref(false)
        const isSpeaking = ref(false)
        const aiVoiceEnabled = ref(true) // Can be toggled by user
        let currentUtterance = null

        // Chat typing state
        const isTyping = ref(false)
        let typingTimer = null
        const TYPING_TIMEOUT = 1000 // Stop typing detection after 1 second of no input

        // PCM Audio Context for real-time streaming
        let audioContext = null
        let currentAudioSource = null
        let pcmSampleRate = 24000 // OpenAI's PCM format is 24kHz, not 16kHz
        let pcmChannels = 1 // Mono audio
        let pcmBitsPerSample = 16 // 16-bit PCM
        let audioPlaybackTime = 0 // Track when to schedule next audio chunk
        
        // AI State Reset
        const isResetting = ref(false)
        
        // Session State
        const sessionStarted = ref(false)
        const showResetWarning = ref(false)
        const showSuccessPopup = ref(false)

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

        // Chat typing detection functions
        const handleTypingActivity = () => {
            // Only trigger typing detection if user actually has text in the field
            if (newMessage.value.trim()) {
                if (!isTyping.value) {
                    handleTypingStart()
                }
                
                // Reset the typing timer to detect when user stops typing
                if (typingTimer) {
                    clearTimeout(typingTimer)
                }
                
                // Set a timer to reset typing state after no input
                typingTimer = setTimeout(() => {
                    isTyping.value = false
                    if (typingTimer) {
                        clearTimeout(typingTimer)
                        typingTimer = null
                    }
                }, TYPING_TIMEOUT)
            }
        }

        const handleTypingStart = () => {
            if (!isTyping.value && props.socket && props.roomId) {
                isTyping.value = true
                console.log('⌨️  CHAT TYPING STARTED - User is composing message')
                
                // Immediately notify backend to cancel any pending timers
                const timerType = props.reflectionSessionId ? 'reflection' : 'ai_agent'
                console.log(`⌨️  Sending typing activity with timer_type: ${timerType}`)
                
                props.socket.emit('chat_typing_activity', {
                    room: props.roomId,
                    userId: props.currentUserId,
                    timestamp: new Date().toISOString(),
                    event: 'typing_start',
                    timer_type: timerType
                })
                console.log('📤 Notified backend of chat typing activity for timer cancellation')
            }
        }

        const sendMessage = () => {
            if (!newMessage.value.trim() || !props.socket) return

            // Reset typing state since message is being sent
            isTyping.value = false
            if (typingTimer) {
                clearTimeout(typingTimer)
                typingTimer = null
            }

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
            
            // Add reflection flag if in reflection mode
            if (props.reflectionSessionId) {
                message.isReflectionMode = true
                console.log('🎓 REFLECTION MODE: Adding isReflectionMode=true flag. Session ID:', props.reflectionSessionId)
            } else {
                console.log('🎓 NOT REFLECTION MODE: reflectionSessionId is empty/undefined:', props.reflectionSessionId)
            }
            
            console.log('Sending message via socket:', message)
            console.log('Socket connected:', props.socket.connected)
            console.log('Socket namespace:', props.socket.nsp)
            
            // Send regular chat message (no special reflection handling)
            props.socket.emit('chat_message', message)

            timerStarted.value = true
            console.log('🕐 Timer started - message sent, waiting for voice activity to cancel')
            
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
            // Play high-quality AI speech audio (legacy single-chunk method)
            if (aiVoiceEnabled.value && data.audioData) {
                playAudioFromBase64(data.audioData, data.messageId || `legacy_${Date.now()}`)
            }
        }

        // Streaming audio state management
        const streamingAudioChunks = ref(new Map()) // messageId -> { chunks: [], totalChunks: 0 }
        const activeAudioStreams = ref(new Set()) // Set of messageIds being streamed

        const handleAudioStreamStart = (data) => {
            if (!aiVoiceEnabled.value) return
            
            const { messageId } = data
            console.log(`🎵 Starting audio stream for message ${messageId}`)
            
            // CRITICAL: Stop all voice recording immediately to prevent feedback
            const wasAutoRecordingActive = autoRecordingEnabled.value
            if (wasAutoRecordingActive) {
                console.log('🔇 IMMEDIATELY stopping voice recording for AI audio stream')
                stopAutoRecording()
                
                // FORCE DISABLE auto recording temporarily to prevent restart
                // We'll re-enable it when streaming completes
                autoRecordingEnabled.value = false
                console.log('🔒 Temporarily disabled auto recording to prevent restart during AI streaming')
            }
            
            // Set speaking state immediately to block any voice input
            isSpeaking.value = true
            
            // Clear any pending speech from the queue to prevent interference
            if (speechQueue.value.length > 0) {
                console.log(`🗑️ Clearing ${speechQueue.value.length} queued speech items - AI is speaking`)
                speechQueue.value = []
                currentAutoTranscript.value = ''
            }
            
            // Initialize streaming state
            streamingAudioChunks.value.set(messageId, {
                chunks: [],
                totalChunks: 0,
                audioBuffers: [],
                wasAutoRecordingActive: wasAutoRecordingActive
            })
            activeAudioStreams.value.add(messageId)
            
            // Reset audio playback timing for smooth streaming
            audioPlaybackTime = 0
        }

        const handleAudioChunk = async (data) => {
            if (!aiVoiceEnabled.value) return
            
            const { messageId, audioData, chunkNumber, isRealtime, format, isComplete, isFinalMarker } = data
            const streamData = streamingAudioChunks.value.get(messageId)
            
            if (!streamData) {
                console.warn(`Received audio chunk for unknown stream: ${messageId}`)
                return
            }
            
            try {
                // Handle final marker (empty chunk that just tells us which was the last real chunk)
                if (isFinalMarker && isComplete) {
                    console.log(`🏁 Received final chunk marker for ${messageId} - chunk ${chunkNumber} was the last real chunk`)
                    
                    // Mark the final chunk number so we know when playback is complete
                    streamData.finalChunkNumber = chunkNumber
                    
                    // Check if that final chunk has already finished playing
                    if (streamData.completedChunks && streamData.completedChunks.has(chunkNumber)) {
                        console.log(`🎯 Final chunk ${chunkNumber} already completed - triggering cleanup`)
                        setTimeout(() => {
                            cleanupAudioStream(messageId)
                        }, 100)
                    }
                    return // Don't process this as a real audio chunk
                }
                
                // Process real audio chunks
                if (audioData) {
                    // Convert base64 to audio buffer
                    const audioBytes = atob(audioData)
                    const audioArray = new Uint8Array(audioBytes.length)
                    for (let i = 0; i < audioBytes.length; i++) {
                        audioArray[i] = audioBytes.charCodeAt(i)
                    }
                    
                    // Store the chunk
                    streamData.chunks.push({
                        number: chunkNumber,
                        data: audioArray
                    })
                    
                    console.log(`📦 Received chunk ${chunkNumber} for message ${messageId} (${audioArray.length} bytes, format: ${format})`)
                    
                    // Real-time PCM playback vs buffered MP3 playback
                    if (format === 'pcm' && isRealtime) {
                        // For PCM format, play chunks immediately as they arrive (true streaming)
                        // We'll determine if it's final when we get the final marker
                        await playPCMChunk(messageId, audioArray, chunkNumber, false)
                    } else {
                        // For MP3 format, wait for all chunks before playing (buffered)
                        // Note: MP3 chunks cannot be played individually - they need to be combined first
                    }
                }
                
            } catch (error) {
                console.error('Error processing audio chunk:', error)
            }
        }

        const handleAudioStreamComplete = async (data) => {
            const { messageId, totalChunks, format } = data
            const streamData = streamingAudioChunks.value.get(messageId)
            
            if (!streamData) {
                console.warn(`Received completion for unknown stream: ${messageId}`)
                return
            }
            
            console.log(`✅ Audio stream complete for ${messageId}: ${totalChunks} chunks received (format: ${format})`)
            
            // For PCM format, chunks are already playing in real-time
            // The final chunk with isComplete=true will trigger cleanup via Web Audio API events
            if (format === 'pcm') {
                console.log(`🎵 PCM real-time streaming complete for ${messageId} - final chunk will trigger cleanup when it finishes playing`)
                // No cleanup needed here - the final chunk's onended event will handle it
            } else {
                // For MP3 format, now combine and play all chunks
                await playStreamingAudioChunks(messageId)
            }
        }

        const playStreamingAudioChunks = async (messageId) => {
            const streamData = streamingAudioChunks.value.get(messageId)
            if (!streamData || streamData.playingStarted) return
            
            streamData.playingStarted = true
            
            try {
                // Sort chunks by number to ensure correct order
                const sortedChunks = streamData.chunks.sort((a, b) => a.number - b.number)
                
                console.log(`🎵 Combining ${sortedChunks.length} MP3 audio chunks for playback`)
                
                // Combine all MP3 audio chunks into a single file
                const totalLength = sortedChunks.reduce((sum, chunk) => sum + chunk.data.length, 0)
                const combinedAudio = new Uint8Array(totalLength)
                
                let offset = 0
                for (const chunk of sortedChunks) {
                    combinedAudio.set(chunk.data, offset)
                    offset += chunk.data.length
                }
                
                console.log(`🔊 Combined MP3 audio: ${totalLength} bytes, playing now...`)
                
                // Create and play audio
                const audioBlob = new Blob([combinedAudio], { type: 'audio/mpeg' })
                const audioUrl = URL.createObjectURL(audioBlob)
                const audio = new Audio(audioUrl)
                
                audio.volume = 0.8
                
                audio.onloadstart = () => {
                    console.log(`🎶 Started loading streamed MP3 audio for message ${messageId}`)
                }
                
                audio.oncanplay = () => {
                    console.log(`✅ Streamed MP3 audio ready to play for message ${messageId}`)
                }
                
                audio.onended = () => {
                    console.log(`🏁 Finished playing streamed MP3 audio for message ${messageId}`)
                    URL.revokeObjectURL(audioUrl)
                    cleanupAudioStream(messageId)
                }
                
                audio.onerror = (error) => {
                    console.error('Streaming MP3 audio playback error:', error)
                    URL.revokeObjectURL(audioUrl)
                    cleanupAudioStream(messageId)
                }
                
                await audio.play()
                console.log(`🔊 Playing ${totalLength} bytes of streamed MP3 audio for message ${messageId}`)
                
            } catch (error) {
                console.error('Error playing streaming MP3 audio:', error)
                cleanupAudioStream(messageId)
            }
        }

        const resumeVoiceRecordingAfterAI = (wasAutoRecordingActive) => {
            console.log(`🔍 resumeVoiceRecordingAfterAI called with wasAutoRecordingActive: ${wasAutoRecordingActive}`)
            console.log(`🔍 Current state - isSpeaking: ${isSpeaking.value}, autoRecordingEnabled: ${autoRecordingEnabled.value}`)
            
            // Check if auto recording should be resumed
            if (wasAutoRecordingActive && !isSpeaking.value) {
                console.log('🎤 Conditions met for voice recording resumption, scheduling...')
                setTimeout(() => {
                    // Double-check the conditions before resuming
                    console.log(`🔍 After delay - isSpeaking: ${isSpeaking.value}, autoRecordingEnabled: ${autoRecordingEnabled.value}`)
                    if (wasAutoRecordingActive && !isSpeaking.value) {
                        console.log('🔓 Re-enabling auto recording after AI finished speaking')
                        autoRecordingEnabled.value = true
                        
                        // Small additional delay to ensure everything is settled
                        setTimeout(() => {
                            console.log(`🔍 Final check - autoRecordingEnabled: ${autoRecordingEnabled.value}, isSpeaking: ${isSpeaking.value}`)
                            if (autoRecordingEnabled.value && !isSpeaking.value) {
                                console.log('🎤 Actually resuming voice recording after AI finished speaking')
                                startAutoRecording()
                            } else {
                                console.log('❌ Failed final check for voice recording resumption')
                            }
                        }, 200)
                    } else {
                        console.log('❌ Failed conditions check after delay')
                    }
                }, 500) // 500ms delay to ensure audio has fully stopped
            } else {
                console.log(`❌ Conditions not met for resumption - wasAutoRecordingActive: ${wasAutoRecordingActive}, isSpeaking: ${isSpeaking.value}`)
            }
        }

        const cleanupAudioStream = (messageId) => {
            const streamData = streamingAudioChunks.value.get(messageId)
            console.log(`🧹 cleanupAudioStream called for ${messageId}`)
            console.log(`🔍 streamData:`, streamData)
            
            // Clean up streaming state
            streamingAudioChunks.value.delete(messageId)
            activeAudioStreams.value.delete(messageId)
            
            // Reset audio timing for next stream
            audioPlaybackTime = 0
            
            console.log(`🧹 Cleaned up audio stream ${messageId}. Active streams remaining: ${activeAudioStreams.value.size}`)
            
            // CRITICAL: Only update speaking state and resume voice recording if NO more streams are active
            if (activeAudioStreams.value.size === 0) {
                console.log('🔇 All audio streams complete - AI finished speaking')
                isSpeaking.value = false
                
                // Notify backend that audio playback is complete so it can release the generation lock
                if (props.socket && props.roomId) {
                    props.socket.emit('ai_audio_playback_complete', {
                        room: props.roomId,
                        messageId: messageId
                    })
                    console.log('📤 Notified backend that AI audio playback is complete')
                }
                
                // Resume voice recording if it was active, with additional safety checks
                console.log(`🔍 Checking voice resumption - streamData?.wasAutoRecordingActive: ${streamData?.wasAutoRecordingActive}`)
                if (streamData?.wasAutoRecordingActive) {
                    console.log('📋 Scheduling voice recording resumption after stream cleanup')
                    resumeVoiceRecordingAfterAI(streamData.wasAutoRecordingActive)
                } else {
                    console.log('🔇 Voice recording was not active before streaming audio')
                }
            } else {
                console.log(`🔄 AI still speaking - ${activeAudioStreams.value.size} active streams remaining`)
            }
        }

        const handleAudioStreamDone = (data) => {
            const { messageId, status, format } = data
            console.log(`🎯 AI audio streaming completely done for ${messageId} with status: ${status}`)
            
            // For PCM format, cleanup is now handled by frontend-based completion detection
            // For MP3 format, we may still need this as a fallback
            if (format !== 'pcm') {
                const streamData = streamingAudioChunks.value.get(messageId)
                if (streamData) {
                    console.log(`🏁 Backend audio stream done for ${messageId} - cleaning up non-PCM stream`)
                    cleanupAudioStream(messageId)
                }
            } else {
                console.log(`🎵 PCM stream done signal received for ${messageId} - frontend completion detection will handle cleanup`)
            }
        }

        const handleAudioError = (data) => {
            const { messageId, error } = data
            console.error(`Audio error for message ${messageId}:`, error)
            
            // Clean up on error
            cleanupAudioStream(messageId)
        }

        const handleUserJoined = (data) => {
            // Update user count from server data
            if (data.userCount !== undefined) {
                onlineUsers.value = data.userCount
            }
            
            // Add system message using the actual joiner's username from backend
            messages.value.push({
                id: Date.now(),
                content: `${data.username || 'Someone'} joined the room`,
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
            
            // Add system message using the actual leaver's username from backend
            messages.value.push({
                id: Date.now(),
                content: `${data.username || 'Someone'} left the room`,
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
            // Voice activity detection for timer cancellation
            recognitionInstance.onspeechstart = () => {
                console.log('🎤 VOICE ACTIVITY DETECTED - User started speaking')
            }
              
            recognitionInstance.onspeechend = () => {
                console.log('🎤 Voice activity ended - User stopped speaking')
            }
            
              
              
            recognitionInstance.onresult = (event) => {
                // CRITICAL: Ignore all speech recognition results while AI is speaking
                if (isSpeaking.value) {
                    console.log('🔇 Ignoring speech input while AI is speaking')
                    return
                }
                
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
                
                // TIMER CANCELLATION: Send when we have transcript and timer was started
                if (currentTranscript && timerStarted.value && props.socket && props.roomId) {
                    props.socket.emit('voice_activity_detected', {
                        room: props.roomId,
                        userId: props.currentUserId,
                        timestamp: new Date().toISOString(),
                        event: 'voice_activity_ongoing'
                    })
                    timerStarted.value = false // Turn off flag after sending
                    console.log('📤 Sent timer cancellation - voice detected after message sent:', currentTranscript.substring(0, 50) + '...')
                }
                
                // For auto mode, queue the speech with timestamp
                if (currentTranscript) {
                    lastSpeechTime.value = Date.now()
                    
                    // Update the current auto transcript for display
                    currentAutoTranscript.value = currentTranscript
                    
                    // Set silence timer for auto mode
                    silenceTimer = setTimeout(() => {
                        // Double-check speaking state before processing
                        if (finalTranscript.trim() && !isSpeaking.value) {
                            queueSpeechForProcessing(finalTranscript.trim(), Date.now())
                            finalTranscript = ''
                            // Clear the auto transcript after queuing
                            setTimeout(() => {
                                currentAutoTranscript.value = ''
                            }, 1000)
                        } else if (isSpeaking.value) {
                            console.log('🔇 Discarding queued speech - AI is speaking')
                            finalTranscript = ''
                            currentAutoTranscript.value = ''
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
                // Restart auto recognition if it's enabled AND AI is not speaking AND no active streams
                if (autoRecordingEnabled.value && !isSpeaking.value && activeAudioStreams.value.size === 0) {
                    setTimeout(() => {
                        if (autoRecordingEnabled.value && !isActive && !isSpeaking.value && activeAudioStreams.value.size === 0) {
                            try {
                                recognitionInstance.start()
                                console.log('🔄 Auto recognition restarted')
                            } catch (error) {
                                console.log('Auto restart failed, retrying...', error)
                                setTimeout(() => {
                                    if (autoRecordingEnabled.value && !isSpeaking.value && activeAudioStreams.value.size === 0) {
                                        startAutoRecording()
                                    }
                                }, 1000)
                            }
                        }
                    }, 100)
                } else if (isSpeaking.value || activeAudioStreams.value.size > 0) {
                    console.log(`🔇 Not restarting voice recognition - AI speaking: ${isSpeaking.value}, Active streams: ${activeAudioStreams.value.size}`)
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
                
                // Periodic check to ensure voice recording doesn't get stuck
                // If auto recording is enabled but not active, and AI is not speaking, restart it
                if (autoRecordingEnabled.value && !isSpeaking.value && activeAudioStreams.value.size === 0 && autoRecognition) {
                    // Check if recognition is actually running by trying to access its state
                    // This is a safety mechanism to prevent voice recording from getting permanently disabled
                    try {
                        // If we can start it without an InvalidStateError, it means it wasn't running
                        const testStart = () => {
                          try {
                            autoRecognition.start()
                            console.log('🔄 Restarted stuck voice recognition')
                          } catch (error) {
                            if (error.name === 'InvalidStateError') {
                              // Already running - this is good
                            } else {
                              console.warn('Voice recognition restart failed:', error)
                            }
                            }
                        }
                        
                        // Only check every 10 seconds to avoid spam
                        const now = Date.now()
                        if (!window.lastVoiceCheck || now - window.lastVoiceCheck > 10000) {
                            window.lastVoiceCheck = now
                            setTimeout(testStart, 100) // Small delay to avoid blocking
                        }
                    } catch (error) {
                        // Ignore errors in the safety check
                    }
                }
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
            
            // CRITICAL: Don't process speech queue while AI is speaking
            if (isSpeaking.value) {
                console.log('🔇 Skipping speech queue processing - AI is speaking')
                return
            }
            
            const now = Date.now()
            const readyItems = speechQueue.value.filter(item => 
                now - item.timestamp > 100 // Wait 100ms before processing
            )
            
            if (readyItems.length === 0) return
            
            isProcessingSpeech.value = true
            
            // Group speech items by user and time (within 3 seconds)
            const groups = groupSpeechByUserAndTime(readyItems, 3000)
            
            groups.forEach(group => {
                // Final check before sending - don't send if AI started speaking
                if (!isSpeaking.value) {
                    // All items in a group are from the same user within the time window
                    const userId = group[0].userId
                    const mergedTranscript = group.map(item => item.transcript).join(' ')
                    sendAutoMessage(mergedTranscript, userId)
                } else {
                    console.log('🔇 Discarding queued speech group - AI started speaking')
                }
                
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
            
            // Add reflection flag if in reflection mode (same as sendMessage)
            if (props.reflectionSessionId) {
                message.isReflectionMode = true
                console.log('🎓 VOICE REFLECTION MODE: Adding isReflectionMode=true flag. Session ID:', props.reflectionSessionId)
            } else {
                console.log('🎓 VOICE NOT REFLECTION MODE: reflectionSessionId is empty/undefined:', props.reflectionSessionId)
            }
            
            // Add to local messages
            messages.value.push(message)
            
            // Send via socket
            if (props.socket) {
                props.socket.emit('chat_message', message)
                
                // Set timer flag since sending a message starts the AI timer
                timerStarted.value = true
                console.log('🕐 Timer started - voice message sent, waiting for voice activity to cancel')
            }
            
            scrollToBottom()
            console.log('Auto-sent message:', transcript)
        }

        const toggleAutoRecording = () => {
            console.log(`🎤 toggleAutoRecording called - current state: ${autoRecordingEnabled.value}`)
            if (!speechSupported.value) {
                console.log('❌ Speech not supported')
                return
            }
            
            autoRecordingEnabled.value = !autoRecordingEnabled.value
            console.log(`🎤 Auto recording toggled to: ${autoRecordingEnabled.value}`)
            
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
            console.log(`🎤 startAutoRecording called`)
            console.log(`🔍 autoRecognition exists: ${!!autoRecognition}`)
            console.log(`🔍 speechSupported: ${speechSupported.value}`)
            console.log(`🔍 isSpeaking: ${isSpeaking.value}`)
            console.log(`🔍 activeAudioStreams.size: ${activeAudioStreams.value.size}`)
            
            if (!autoRecognition || !speechSupported.value) {
                console.log('❌ Cannot start auto recording - missing recognition or unsupported')
                return
            }
            
            // Don't start recording if AI is currently speaking
            if (isSpeaking.value) {
                console.log('🔇 Not starting voice recording - AI is speaking')
                return
            }
            
            // Additional check for active audio streams
            if (activeAudioStreams.value.size > 0) {
                console.log(`🔇 Not starting voice recording - ${activeAudioStreams.value.size} active audio streams`)
                return
            }
            
            try {
                autoRecognition.start()
                console.log('🎤 Auto recording started successfully')
            } catch (error) {
                console.error('Error starting auto recording:', error)
                // If already running, that's okay
                if (error.name !== 'InvalidStateError') {
                    console.log('❌ Disabling auto recording due to error')
                    autoRecordingEnabled.value = false
                } else {
                    console.log('✅ Auto recognition was already running')
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
        const initTextToSpeech = async () => {
            // Check if Web Audio API is supported for high-quality audio playback
            if ('AudioContext' in window || 'webkitAudioContext' in window) {
                ttsSupported.value = true
                console.log('High-quality audio playback supported')
                
                // Initialize PCM audio context for real-time streaming
                await initializePCMAudio()
            } else {
                ttsSupported.value = false
                console.log('High-quality audio playback not supported')
            }
        }

        const playAudioFromBase64 = async (base64Audio, messageId = null) => {
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
                
                // Clear any pending speech from the queue to prevent interference
                if (speechQueue.value.length > 0) {
                    console.log(`🗑️ Clearing ${speechQueue.value.length} queued speech items - AI is speaking`)
                    speechQueue.value = []
                    currentAutoTranscript.value = ''
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
                    console.log('✅ Finished playing AI speech (legacy)')
                    
                    // Notify backend that audio playback is complete for legacy audio too
                    if (props.socket && props.roomId && messageId) {
                        props.socket.emit('ai_audio_playback_complete', {
                            room: props.roomId,
                            messageId: messageId
                        })
                        console.log(`📤 Notified backend that legacy AI audio playback is complete (${messageId})`)
                    }
                    
                    // Resume voice recording after AI finishes speaking (with delay)
                    console.log(`🔍 Legacy audio ended, wasAutoRecordingActive: ${wasAutoRecordingActive}`)
                    if (wasAutoRecordingActive) {
                        console.log('🎤 Scheduling voice recording resumption after legacy AI audio')
                        resumeVoiceRecordingAfterAI(wasAutoRecordingActive)
                    } else {
                        console.log('🔇 Voice recording was not active before legacy AI audio')
                    }
                }
                
                audio.onerror = (error) => {
                    console.error('Audio playback error:', error)
                    isSpeaking.value = false
                    currentUtterance = null
                    URL.revokeObjectURL(audioUrl)
                    
                    // Notify backend even if audio failed
                    if (props.socket && props.roomId && messageId) {
                        props.socket.emit('ai_audio_playback_complete', {
                            room: props.roomId,
                            messageId: messageId
                        })
                        console.log(`📤 Notified backend that legacy AI audio playback failed (${messageId})`)
                    }
                    
                    // Resume voice recording even if audio failed
                    if (wasAutoRecordingActive) {
                        resumeVoiceRecordingAfterAI(wasAutoRecordingActive)
                    }
                }
                
                currentUtterance = audio
                await audio.play()
                
            } catch (error) {
                console.error('Error playing audio:', error)
                isSpeaking.value = false
                currentUtterance = null
                
                // Notify backend even if audio failed
                if (props.socket && props.roomId, messageId) {
                    props.socket.emit('ai_audio_playback_complete', {
                        room: props.roomId,
                        messageId: messageId
                    })
                    console.log(`📤 Notified backend that legacy AI audio playback errored (${messageId})`)
                }
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
            }
            
            // Stop PCM audio if playing
            stopPCMAudio()
            
            isSpeaking.value = false
            currentUtterance = null
        }

        const toggleAIVoice = () => {
            aiVoiceEnabled.value = !aiVoiceEnabled.value
            if (!aiVoiceEnabled.value) {
                stopSpeaking()
            }
            console.log('AI voice', aiVoiceEnabled.value ? 'enabled' : 'disabled')
        }        // PCM audio functions
        const initializePCMAudio = async () => {
            try {
                // Initialize Web Audio API context
                const AudioContext = window.AudioContext || window.webkitAudioContext
                if (!AudioContext) {
                    console.warn('Web Audio API not supported - falling back to MP3 buffering')
                    return false
                }

                audioContext = new AudioContext()
                
                // Resume audio context if suspended (browser policy)
                if (audioContext.state === 'suspended') {
                    await audioContext.resume()
                }
                
                console.log(`✅ PCM Audio Context initialized for real-time streaming (24kHz OpenAI PCM format)`)
                console.log(`🎵 Audio Context State: ${audioContext.state}`)
                console.log(`🔧 Audio Context Sample Rate: ${audioContext.sampleRate}Hz`)
                console.log(`🎤 PCM Format: 24kHz, 16-bit, mono`)
                
                return true
            } catch (error) {
                console.error('Failed to initialize PCM audio context:', error)
                return false
            }
        }

        const playPCMChunk = async (messageId, pcmData, chunkNumber, isLastChunk = false) => {
            if (!audioContext) {
                // Try to initialize if not already done
                const initialized = await initializePCMAudio()
                if (!initialized) {
                    console.warn('PCM audio not available, falling back to buffered playback')
                    return
                }
            }

            try {
                // Validate PCM data length
                if (pcmData.length % 2 !== 0) {
                    console.warn(`PCM chunk ${chunkNumber} has odd length: ${pcmData.length} bytes`)
                    return
                }

                // Convert PCM bytes to Float32Array for Web Audio API
                const samples = new Float32Array(pcmData.length / 2)
                const dataView = new DataView(pcmData.buffer)
                
                for (let i = 0; i < samples.length; i++) {
                    // Convert 16-bit PCM to float (-1.0 to 1.0)
                    const sample = dataView.getInt16(i * 2, true) // little-endian
                    samples[i] = sample / 32768.0
                }

                // Create audio buffer with OpenAI's PCM format (24kHz)
                const audioBuffer = audioContext.createBuffer(pcmChannels, samples.length, pcmSampleRate)
                audioBuffer.getChannelData(0).set(samples)

                // Create and play audio source
                const source = audioContext.createBufferSource()
                source.buffer = audioBuffer
                source.connect(audioContext.destination)
                
                // For immediate real-time playback, schedule based on current context time
                const currentTime = audioContext.currentTime
                const chunkDuration = samples.length / pcmSampleRate
                
                // Start immediately if first chunk, otherwise schedule seamlessly
                let startTime = currentTime
                if (chunkNumber === 1) {
                    // First chunk - start immediately
                    audioPlaybackTime = currentTime
                } else {
                    // Subsequent chunks - schedule to play after previous chunk
                    startTime = Math.max(currentTime, audioPlaybackTime)
                }
                
                // Schedule the chunk to play
                source.start(startTime)
                
                // Update timing for next chunk
                audioPlaybackTime = startTime + chunkDuration
                
                console.log(`🎵 Playing PCM chunk ${chunkNumber} at ${startTime.toFixed(3)}s (${samples.length} samples @ ${pcmSampleRate}Hz, duration: ${chunkDuration.toFixed(3)}s)${isLastChunk ? ' [FINAL CHUNK]' : ''}`)

                // Handle end of chunk
                source.onended = () => {
                    console.log(`✅ PCM chunk ${chunkNumber} playback completed`)
                    
                    // Mark this chunk as completed for tracking
                    const streamData = streamingAudioChunks.value.get(messageId)
                    if (streamData) {
                        if (!streamData.completedChunks) {
                            streamData.completedChunks = new Set()
                        }
                        streamData.completedChunks.add(chunkNumber)
                        
                        // Check if this was the final chunk and if so, trigger cleanup
                        if (streamData.finalChunkNumber && chunkNumber === streamData.finalChunkNumber) {
                            console.log(`🏁 FINAL PCM chunk ${chunkNumber} completed - triggering voice recording resumption`)
                            
                            // Use a timeout that accounts for any remaining audio buffer in the system
                            setTimeout(() => {
                                console.log(`🎯 Final PCM audio playback complete for ${messageId} - safe to resume voice recording`)
                                cleanupAudioStream(messageId)
                            }, 100) // Small delay to ensure all audio system buffers have finished
                        }
                    }
                }

            } catch (error) {
                console.error(`Error playing PCM chunk ${chunkNumber}:`, error)
                console.error('PCM data length:', pcmData.length, 'bytes')
                console.error('Expected format: 24kHz, 16-bit, mono PCM')
            }
        }

        const stopPCMAudio = () => {
            // Reset audio playback timing
            audioPlaybackTime = 0
            
            if (currentAudioSource) {
                try {
                    currentAudioSource.stop()
                    currentAudioSource = null
                } catch (error) {
                    console.error('Error stopping PCM audio:', error)
                }
            }
            
            console.log('🔇 PCM audio playback stopped and timing reset')
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
                    handleUserLeft(data) // Use the same handler as user_left
                })

                props.socket.on('ai_speech', (data) => {
                    console.log('Received AI speech:', data)
                    handleAISpeech(data)
                })

                // Handle streaming audio events
                props.socket.on('ai_audio_stream_start', (data) => {
                    console.log('AI audio stream started:', data)
                    handleAudioStreamStart(data)
                })

                props.socket.on('ai_audio_chunk', (data) => {
                    console.log('Received AI audio chunk:', data.chunkNumber, data.totalBytes)
                    handleAudioChunk(data)
                })

                props.socket.on('ai_audio_complete', (data) => {
                    console.log('AI audio stream complete:', data)
                    handleAudioStreamComplete(data)
                })

                props.socket.on('ai_audio_done', (data) => {
                    console.log('AI audio streaming completely done:', data)
                    handleAudioStreamDone(data)
                })

                props.socket.on('ai_audio_error', (data) => {
                    console.log('AI audio error:', data)
                    handleAudioError(data)
                })

                // Session state synchronization events
                props.socket.on('session_state_changed', (data) => {
                    console.log('🔄 Session state changed:', data)
                    handleSessionStateChange(data)
                })

                // Reflection session event listeners
                props.socket.on('reflection_started', (data) => {
                    console.log('🎓 FRONTEND: Reflection session started event received:', data)
                    
                    // Update reflection session ID from backend
                    if (data.session_id) {
                        emit('reflection-session-started', data.session_id)
                        console.log('🎓 FRONTEND: Updated reflection session ID:', data.session_id)
                    }
                    
                    // Add separator line
                    if (data.separator) {
                        addReflectionMessage('─── 🎓 Learning Reflection Session Started ───', 'System', false, true, false)
                    }
                    
                    addReflectionMessage(data.message, 'Bob', true, false, data.hasAudio || false)
                    console.log('🎓 FRONTEND: Added reflection messages to chat')
                })

                props.socket.on('reflection_message', (data) => {
                    console.log('🎓 FRONTEND: Reflection message event received:', data)
                    if (data.session_id === props.reflectionSessionId) {
                        addReflectionMessage(data.message, 'Bob', true, false, data.hasAudio || false)
                    } else {
                        console.log('🎓 FRONTEND: Session ID mismatch, ignoring message')
                    }
                })

                props.socket.on('reflection_ended', (data) => {
                    console.log('🎓 Reflection session ended:', data)
                    if (data.session_id === props.reflectionSessionId) {
                        addReflectionMessage(data.message, 'Bob', true, false, data.hasAudio || false)
                        
                        // Add session summary if available (only for natural endings, not user-initiated)
                        if (data.summary && !data.user_initiated) {
                            const summaryText = `Session Summary: ${data.summary.questions_discussed} questions discussed, ${data.summary.code_sections_reviewed} code sections reviewed.`
                            addReflectionMessage(summaryText, 'System', false, true, false)
                        }
                        
                        // Add appropriate end separator
                        const separatorText = data.user_initiated 
                            ? '─── 🎓 Reflection Mode Disabled ───'
                            : '─── 🎓 Reflection Session Complete ───'
                        addReflectionMessage(separatorText, 'System', false, true, false)
                    }
                })

                props.socket.on('reflection_error', (data) => {
                    console.error('❌ Reflection error:', data)
                    const userFriendlyMessage = data.message.includes('not available') 
                        ? 'Reflection feature is temporarily unavailable. Please try again later.'
                        : `Reflection error: ${data.message}`
                    addReflectionMessage(userFriendlyMessage, 'System', false, true, false)
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
            
            // Clear typing timer
            if (typingTimer) {
                clearTimeout(typingTimer)
            }
            
            if (props.socket) {
                props.socket.off('chat_message', handleIncomingMessage)
                props.socket.off('user_joined', handleUserJoined)
                props.socket.off('user_left', handleUserLeft)
                props.socket.off('user_count_update', handleUserCountUpdate)
                props.socket.off('user_disconnected', handleUserCountUpdate)
                props.socket.off('ai_speech', handleAISpeech)
                props.socket.off('ai_audio_stream_start', handleAudioStreamStart)
                props.socket.off('ai_audio_chunk', handleAudioChunk)
                props.socket.off('ai_audio_complete', handleAudioStreamComplete)
                props.socket.off('ai_audio_done', handleAudioStreamDone)
                props.socket.off('ai_audio_error', handleAudioError)
                props.socket.off('session_state_changed', handleSessionStateChange)
            }
        })

        // Add a function to manually add messages (for CodeRunner integration)
        const addMessage = (message) => {
            messages.value.push(message)
            scrollToBottom()
        }

        const addReflectionMessage = (content, username, isAI = false, isSystem = false, hasAudio = false) => {
            console.log('🎓 FRONTEND: addReflectionMessage called:', { content, username, isAI, isSystem, hasAudio })
            
            const message = {
                id: Date.now() + Math.random(), // Ensure uniqueness
                content: content,
                userId: isAI ? 'ai_agent_bob' : 'system',
                username: username,
                timestamp: new Date().toISOString(),
                room: props.roomId,
                isAI: isAI,
                isSystem: isSystem,
                isReflection: true,
                hasAudio: hasAudio  // Indicate if server will provide audio
            }
            
            console.log('🎓 FRONTEND: Adding message to messages array:', message)
            messages.value.push(message)
            console.log('🎓 FRONTEND: Messages count after push:', messages.value.length)
            scrollToBottom()
            
            // Only use browser TTS if server doesn't provide audio
            if (isAI && aiVoiceEnabled.value && !hasAudio) {
                speakMessage(content, true)
            }
        }

        // Session control functions
        const startSession = async () => {
            console.log('🚀 Starting pair programming session...')
            sessionStarted.value = true
            
            try {
                // Call backend API to start session and send Bob greeting
                const response = await fetch('/api/start-session', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        room_id: props.roomId
                    })
                })
                
                const result = await response.json()
                
                if (response.ok && result.success) {
                    console.log('✅ Session started successfully:', result)
                } else {
                    console.error('❌ Failed to start session:', result.error)
                }
            } catch (error) {
                console.error('❌ Error starting session:', error)
            }
            
            // No longer adding a system message here - Bob will send its greeting
            scrollToBottom()
        }

        const confirmResetSession = async () => {
            console.log('🔄 Confirming session reset...')
            showResetWarning.value = false
            isResetting.value = true
            
            try {
                // 1. Reset AI agent state via API
                const response = await fetch('/api/reset-ai-state', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        room_id: props.roomId
                    })
                })
                
                const result = await response.json()
                
                if (response.ok && result.success) {
                    console.log('✅ AI agent state reset successfully:', result)
                    
                    // 2. Stop any active reflection session (always emit end event to ensure parent clears state)
                    if (props.reflectionSessionId) {
                        console.log(`🎓 Stopping active reflection session during reset: ${props.reflectionSessionId}`)
                        props.socket.emit('toggle_reflection', {
                            room: props.roomId,
                            action: 'stop'
                        })
                    }
                    // Always emit reflection ended to ensure parent clears reflection state
                    emit('reflection-session-ended')
                    console.log('🎓 Emitted reflection-session-ended to parent during reset')
                    
                    // 3. Clear all chat messages and reset session state
                    messages.value = []
                    currentAutoTranscript.value = ''
                    speechQueue.value = []
                    isSpeaking.value = false
                    sessionStarted.value = false
                    
                    // 4. Show success popup
                    showSuccessPopup.value = true
                    setTimeout(() => {
                        showSuccessPopup.value = false
                    }, 3000)
                    
                    console.log('✅ Session reset completed - messages cleared, session stopped, and reflection ended')
                    
                } else {
                    console.error('❌ Failed to reset session:', result)
                    alert('Failed to reset session: ' + (result.error || 'Unknown error'))
                }
                
            } catch (error) {
                console.error('❌ Error resetting session:', error)
                alert('Error resetting session: ' + error.message)
            }
            
            isResetting.value = false
        }

        // Enhanced reset AI state function (legacy - replaced by confirmResetSession)
        const resetAIState = async () => {
            console.log('🔄 Resetting AI agent state...')
            isResetting.value = true
            
            try {
                // Call backend API to reset AI agent state
                const response = await fetch('/api/reset-ai-state', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        room_id: props.roomId
                    })
                })
                
                const result = await response.json()
                
                if (response.ok && result.success) {
                    console.log('✅ AI agent state reset successfully:', result)
                    
                    // Reset local chat messages (optional - you might want to keep chat history)
                    // messages.value = []
                    
                    // Reset local speech state
                    currentAutoTranscript.value = ''
                    speechQueue.value = []
                    isSpeaking.value = false
                    
                    // Show success message in chat
                    const resetMessage = {
                        id: `reset_${Date.now()}`,
                        content: '🔄 AI agent state has been reset. Fresh start!',
                        username: 'System',
                        userId: 'system',
                        timestamp: new Date().toISOString(),
                        room: props.roomId,
                        isSystem: true,
                        isAI: false
                    }
                    messages.value.push(resetMessage)
                    scrollToBottom()
                    
                } else {
                    console.error('❌ Failed to reset AI agent state:', result)
                    alert('Failed to reset AI state: ' + (result.error || 'Unknown error'))
                }
                
            } catch (error) {
                console.error('❌ Error resetting AI agent state:', error)
                alert('Error resetting AI state: ' + error.message)
            }
            
            isResetting.value = false
        }

        const handleSessionStateChange = (data) => {
            console.log('🔄 PairChat: Handling session state change:', data)
            
            if (data.action === 'session_started') {
                // Update session started state if not initiated by this user
                if (!sessionStarted.value) {
                    sessionStarted.value = true
                    console.log('📡 Session started by another user - updating local state')
                }
            } else if (data.action === 'session_reset') {
                // Update session state if not initiated by this user
                if (sessionStarted.value || messages.value.length > 0) {
                    sessionStarted.value = false
                    messages.value = []
                    currentAutoTranscript.value = ''
                    speechQueue.value = []
                    isSpeaking.value = false
                    console.log('📡 Session reset by another user - updating local state')
                }
            } else if (data.action === 'reflection_started') {
                // Emit reflection started event to parent components
                emit('reflection-session-started', data.session_id || 'reflection_' + Date.now())
                console.log('📡 Reflection started by another user - notifying parent')
            } else if (data.action === 'reflection_stopped') {
                // Emit reflection stopped event to parent components
                emit('reflection-session-ended')
                console.log('📡 Reflection stopped by another user - notifying parent')
            }
            
            // Show notification message for cross-user actions
            if (data.message) {
                const notification = {
                    id: 'session_sync_' + Date.now(),
                    content: `ℹ️ ${data.message}`,
                    username: 'System',
                    userId: 'system',
                    timestamp: new Date().toISOString(),
                    room: props.roomId,
                    isSystem: true,
                    isNotification: true
                }
                messages.value.push(notification)
                scrollToBottom()
            }
        }

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
            isTyping,
            isResetting,
            sessionStarted,
            showResetWarning,
            showSuccessPopup,
            formatTime,
            sendMessage,
            addMessage,
            addReflectionMessage,
            toggleAutoRecording,
            toggleAIVoice,
            dismissTooltip,
            handleTypingActivity,
            handleTypingStart,
            startSession,
            confirmResetSession
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

.header-controls {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.reset-ai-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    background: #f97316;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 0.75rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
}

.reset-ai-btn:hover:not(:disabled) {
    background: #ea580c;
    transform: translateY(-1px);
}

.reset-ai-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
}

.reset-ai-btn:active {
    transform: translateY(0);
}

.session-controls {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.start-session-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    background: #10b981;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
}

.start-session-btn:hover {
    background: #059669;
    transform: translateY(-1px);
}

.reset-session-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    background: #fce7e6;
    color: #dc2626;
    border: 1px solid #dc2626;
    border-radius: 8px;
    font-size: 0.75rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
}

.reset-session-btn:hover:not(:disabled) {
    background: #fca5a5;
    border-color: #b91c1c;
    color: #b91c1c;
    transform: translateY(-1px);
}

.reset-session-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
}

/* Chat message styles */
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

.message.ai-reflection-message {
    background: linear-gradient(135deg, #dbeafe, #bae6fd);
    color: #1e40af;
    align-self: flex-start;
    border-left: 4px solid #0ea5e9;
    box-shadow: 0 2px 8px rgba(14, 165, 233, 0.3);
    border-radius: 12px;
}

.message.ai-execution-help {
    background: linear-gradient(135deg, #dbeafe, #bae6fd);
    color: #1e40af;
    align-self: flex-start;
    border-left: 4px solid #0ea5e9;
    box-shadow: 0 2px 8px rgba(14, 165, 233, 0.3);
    border-radius: 12px;
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
    background: #cbd5e0;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
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

/* Modal styles */
.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.modal {
    background: white;
    border-radius: 12px;
    padding: 0;
    max-width: 500px;
    width: 90%;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

.modal-header {
    padding: 1.5rem 1.5rem 0 1.5rem;
    border-bottom: 1px solid #e5e7eb;
}

.modal-header h3 {
    margin: 0 0 1rem 0;
    font-size: 1.25rem;
    font-weight: 600;
    color: #dc2626;
}

.modal-body {
    padding: 1.5rem;
}

.modal-body p {
    margin: 0 0 1rem 0;
    color: #374151;
}

.warning-text {
    font-weight: 600;
    color: #dc2626;
}

.reset-actions {
    margin: 1rem 0;
    padding-left: 1.5rem;
}

.reset-actions li {
    margin: 0.5rem 0;
    color: #6b7280;
}

.warning-note {
    color: #dc2626;
    font-weight: 600;
    text-align: center;
    padding: 1rem;
    background: #fef2f2;
    border-radius: 8px;
    margin-top: 1rem;
}

.modal-footer {
    padding: 1rem 1.5rem 1.5rem 1.5rem;
    display: flex;
    gap: 1rem;
    justify-content: flex-end;
}

.cancel-btn {
    padding: 0.5rem 1rem;
    background: #f3f4f6;
    color: #374151;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 500;
}

.cancel-btn:hover {
    background: #e5e7eb;
}

.confirm-reset-btn {
    padding: 0.5rem 1rem;
    background: #dc2626;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 500;
}

.confirm-reset-btn:hover:not(:disabled) {
    background: #b91c1c;
}

.confirm-reset-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

/* Success Popup */
.success-popup {
    position: fixed;
    top: 2rem;
    right: 2rem;
    background: #10b981;
    color: white;
    padding: 1rem 1.5rem;
    border-radius: 8px;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    z-index: 1001;
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

.success-content {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.success-icon {
    font-size: 1.25rem;
}

.success-text {
    font-weight: 500;
}

/* Small popups near reset button */
.reset-warning-popup {
    position: absolute;
    top: calc(100% + 8px);
    right: 0;
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    z-index: 1001;
    min-width: 280px;
    animation: slideDown 0.2s ease-out;
}

.popup-content {
    padding: 1rem;
}

.popup-header h4 {
    margin: 0 0 0.5rem 0;
    font-size: 0.9rem;
    font-weight: 600;
    color: #f59e0b;
}

.popup-body p {
    margin: 0 0 1rem 0;
    font-size: 0.8rem;
    color: #6b7280;
    line-height: 1.4;
}

.popup-actions {
    display: flex;
    gap: 0.5rem;
    justify-content: flex-end;
}

.cancel-btn-small, .confirm-btn-small {
    padding: 0.4rem 0.8rem;
    border: none;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.2s;
}

.cancel-btn-small {
    background: #f3f4f6;
    color: #6b7280;
}

.cancel-btn-small:hover {
    background: #e5e7eb;
}

.confirm-btn-small {
    background: #ef4444;
    color: white;
}

.confirm-btn-small:hover:not(:disabled) {
    background: #dc2626;
}

.confirm-btn-small:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.success-popup-small {
    position: absolute;
    top: calc(100% + 8px);
    right: 0;
    background: #10b981;
    color: white;
    padding: 0.7rem 1rem;
    border-radius: 6px;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    z-index: 1001;
    animation: slideDown 0.2s ease-out;
}

.success-content-small {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    font-weight: 500;
}

@keyframes slideDown {
    from {
        transform: translateY(-10px);
        opacity: 0;
    }
    to {
        transform: translateY(0);
        opacity: 1;
    }
}
</style>
