"""
AI Audio Service - Handles TTS audio generation and streaming
"""

import asyncio
import base64
import threading
import time
from datetime import datetime
from typing import Optional

from openai import AsyncOpenAI


class AIAudioService:
    def __init__(self, socketio_instance, async_client: AsyncOpenAI, agent_name: str, agent_id: str):
        self.socketio = socketio_instance
        self.async_client = async_client
        self.agent_name = agent_name
        self.agent_id = agent_id
        
        # Voice configuration
        self.voice_config = {
            "model": "tts-1",            # Use OpenAI's fast TTS model (tts-1 or tts-1-hd)
            "voice": "echo",             # Available: alloy, echo, fable, onyx, nova, shimmer
            "speed": 1.1                 # 0.25 to 4.0
        }

    async def generate_speech(self, text: str) -> Optional[bytes]:
        """Generate speech audio from text using OpenAI TTS"""
        if not self.async_client:
            return None
            
        try:
            # Limit text length to avoid very long audio files (70 words ≈ 350-500 chars)
            if len(text) > 500:
                text = text[:500] + "..."
            
            response = self.async_client.audio.speech.create(
                model=self.voice_config["model"],
                voice=self.voice_config["voice"],
                input=text,
                speed=self.voice_config["speed"]
            )
            
            # Return the audio bytes
            return response.content
            
        except Exception as e:
            print(f"Error generating speech: {e}")
            return None

    async def generate_streaming_speech(self, text: str, room_id: str, message_id: str):
        """Generate streaming speech audio using OpenAI's streaming TTS API"""
        if not self.async_client:
            return None
            
        try:
            # Limit text length to avoid very long audio files (70 words ≈ 350-500 chars)
            if len(text) > 500:
                text = text[:500] + "..."
            
            # Signal start of streaming
            self.socketio.emit('ai_audio_stream_start', {
                'messageId': message_id,
                'room': room_id
            }, room=room_id, namespace='/ws')
            
            chunk_number = 0
            total_bytes_sent = 0
            
            print(f"🎤 Starting to stream audio for text: '{text[:50]}...'")
            
            # Use OpenAI's official streaming approach with AsyncOpenAI
            async with self.async_client.audio.speech.with_streaming_response.create(
                model=self.voice_config["model"],  # tts-1
                voice=self.voice_config["voice"],  # nova
                input=text,
                speed=self.voice_config["speed"],
                response_format="pcm"  # PCM for true real-time streaming
            ) as response:
                chunks_sent = []
                # Stream chunks directly as they arrive - TRUE real-time streaming
                async for chunk in response.iter_bytes(chunk_size=1024 * 2):  # 2KB chunks for PCM real-time
                    if chunk:
                        chunk_number += 1
                        total_bytes_sent += len(chunk)
                        chunk_base64 = base64.b64encode(chunk).decode('utf-8')
                        chunks_sent.append(chunk_number)
                        
                        # Send chunk immediately as it arrives from OpenAI
                        self.socketio.emit('ai_audio_chunk', {
                            'messageId': message_id,
                            'audioData': chunk_base64,
                            'chunkNumber': chunk_number,
                            'totalBytes': total_bytes_sent,
                            'room': room_id,
                            'isComplete': False,  # We don't know if this is the last chunk yet
                            'isRealtime': True,
                            'format': 'pcm'  # PCM format for true real-time streaming
                        }, room=room_id, namespace='/ws')

                # Send a special "final chunk" marker
                if chunks_sent:
                    final_chunk_number = chunks_sent[-1]
                    
                    # Send a special "final chunk" marker
                    self.socketio.emit('ai_audio_chunk', {
                        'messageId': message_id,
                        'audioData': '',  # Empty data
                        'chunkNumber': final_chunk_number,
                        'totalBytes': total_bytes_sent,
                        'room': room_id,
                        'isComplete': True,  # Mark as final
                        'isRealtime': True,
                        'format': 'pcm',
                        'isFinalMarker': True  # Special flag to indicate this is just a marker
                    }, room=room_id, namespace='/ws')

                # Signal completion - only that streaming is done, not that playback is done
                self.socketio.emit('ai_audio_complete', {
                    'messageId': message_id,
                    'room': room_id,
                    'totalChunks': chunk_number,
                    'totalBytes': total_bytes_sent,
                    'format': 'pcm'
                }, room=room_id, namespace='/ws')
                
                print(f"✅ Streamed {chunk_number} PCM chunks ({total_bytes_sent} bytes) in real-time for message {message_id}")
            return True
            
        except Exception as e:
            print(f"Error generating streaming speech: {e}")
            # Signal error
            self.socketio.emit('ai_audio_error', {
                'messageId': message_id,
                'room': room_id,
                'error': str(e)
            }, room=room_id, namespace='/ws')
            
            # CRITICAL: Even on error, signal that audio streaming is done
            self.socketio.emit('ai_audio_done', {
                'messageId': message_id,
                'room': room_id,
                'status': 'error'
            }, room=room_id, namespace='/ws')
            
            return None

    async def send_ai_message_with_audio(self, room_id: str, content: str, is_reflection: bool = False, 
                                       is_execution_help: bool = False, conversation_history=None):
        """Send an AI message to the chat room with streaming audio - optimized for speed"""
        message_type = "ai_exec" if is_execution_help else "ai"
        
        message = {
            'id': f"{message_type}_{int(time.time() * 1000)}",
            'content': content,
            'username': self.agent_name,
            'userId': self.agent_id,
            'timestamp': datetime.now().isoformat(),
            'room': room_id,
            'isAI': True,
            'isReflection': is_reflection,
            'isExecutionHelp': is_execution_help,
            'hasAudio': True,  # Will have streaming audio
            'isStreaming': True  # Indicate this is a streaming response
        }
        
        # Update last response time for cooldown tracking
        if conversation_history and room_id in conversation_history:
            context = conversation_history[room_id]
            context.last_ai_response = datetime.now()
            print(f"🔒 AI RESPONSE: Tracking response time for cooldown in room {room_id}")
        
        # Send message immediately (don't wait for audio)
        self.socketio.emit('chat_message', message, room=room_id, namespace='/ws')
        
        # Generate streaming audio in parallel (non-blocking)
        def generate_and_stream_audio():
            try:
                # Run the async audio streaming in a new event loop
                async def audio_task():
                    await self.generate_streaming_speech(content, room_id, message['id'])
                
                # Create and run new event loop for audio generation
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(audio_task())
                loop.close()
            except Exception as e:
                print(f"Error in streaming audio: {e}")
                # Fallback to simple notification that audio failed
                self.socketio.emit('ai_audio_error', {
                    'messageId': message['id'],
                    'room': room_id,
                    'error': 'Audio generation failed'
                }, room=room_id, namespace='/ws')
        
        # Start audio streaming in a separate thread
        threading.Thread(target=generate_and_stream_audio, daemon=True).start()
        
        return message

    def send_ai_message_text_only(self, room_id: str, content: str, is_reflection: bool = False, 
                                 is_execution_help: bool = False, conversation_history=None):
        """Send an AI message to the chat room without audio"""
        message_type = "ai_exec" if is_execution_help else "ai"
        
        message = {
            'id': f"{message_type}_{int(time.time() * 1000)}",
            'content': content,
            'username': self.agent_name,
            'userId': self.agent_id,
            'timestamp': datetime.now().isoformat(),
            'room': room_id,
            'isAI': True,
            'isReflection': is_reflection,
            'isExecutionHelp': is_execution_help,
            'hasAudio': False
        }
        
        # Update last response time for non-greeting messages
        if conversation_history and room_id in conversation_history:
            conversation_history[room_id].last_ai_response = datetime.now()
            
        # Emit the message to the room (no audio)
        self.socketio.emit('chat_message', message, room=room_id, namespace='/ws')
        
        return message

    def send_ai_message(self, room_id: str, content: str, is_reflection: bool = False, 
                       is_execution_help: bool = False, conversation_history=None):
        """Send an AI message to the chat room (optimized sync version)"""
        try:
            # Try to use existing event loop if available
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self.send_ai_message_with_audio(
                    room_id, content, is_reflection, is_execution_help, conversation_history))
                return
            except RuntimeError:
                # No running loop - use thread pool to avoid blocking
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.send_ai_message_with_audio(
                        room_id, content, is_reflection, is_execution_help, conversation_history))
                    return
        except Exception as e:
            # Fallback to simple text-only message
            return self.send_ai_message_text_only(room_id, content, is_reflection, is_execution_help, conversation_history)

    def set_voice_config(self, voice: str = None, model: str = None, speed: float = None):
        """Update voice configuration for TTS"""
        if voice and voice in ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]:
            self.voice_config["voice"] = voice
        if model and model in ["tts-1", "tts-1-hd"]:
            self.voice_config["model"] = model
        if speed and 0.25 <= speed <= 4.0:
            self.voice_config["speed"] = speed
