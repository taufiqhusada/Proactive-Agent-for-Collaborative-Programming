"""
AI Audio Service - Handles TTS audio generation
"""

import asyncio
import base64
import threading
import time
from datetime import datetime
from typing import Optional

from openai import OpenAI, AsyncOpenAI, DefaultAioHttpClient


class AIAudioService:
    def __init__(self, socketio_instance, client: OpenAI, agent_name: str, agent_id: str):
        self.socketio = socketio_instance
        self.client = client
        self.agent_name = agent_name
        self.agent_id = agent_id
        
        # Store client for API key access (no need to pre-create async client)
        # We'll use async with pattern for proper resource management
        
        # Voice configuration
        self.voice_config = {
            "model": "tts-1",            # Use OpenAI's fast TTS model (tts-1 or tts-1-hd)
            "voice": "echo",             # Available: alloy, echo, fable, onyx, nova, shimmer
            "speed": 1.1                 # 0.25 to 4.0
        }

    # OBSOLETE: This method is no longer used
    # def generate_speech(self, text: str) -> Optional[bytes]:
    #     """Generate speech audio from text using OpenAI TTS"""
    #     if not self.client:
    #         return None
            
    #     try:
    #         # Limit text length to avoid very long audio files (70 words ≈ 350-500 chars)
    #         if len(text) > 500:
    #             text = text[:500] + "..."
            
    #         response = self.client.audio.speech.create(
    #             model=self.voice_config["model"],
    #             voice=self.voice_config["voice"],
    #             input=text,
    #             speed=self.voice_config["speed"]
    #         )
            
    #         # Return the audio bytes
    #         return response.content
            
    #     except Exception as e:
    #         print(f"Error generating speech: {e}")
    #         return None

    def generate_streaming_speech(self, text: str, room_id: str, message_id: str):
        """Generate streaming speech audio using OpenAI's streaming TTS API with async inside"""
        if not self.client:
            return None
            
        async def _async_generate_streaming():
            """Internal async function for true streaming audio with aiohttp backend"""
            
            try:
                # Use async with pattern for proper resource management with aiohttp
                async with AsyncOpenAI(
                    api_key=self.client.api_key,
                    http_client=DefaultAioHttpClient()
                ) as async_client:
                    
                    # Limit text length to avoid very long audio files (70 words ≈ 350-500 chars)
                    limited_text = text[:500] + "..." if len(text) > 500 else text
                    
                    # Signal start of streaming
                    self.socketio.emit('ai_audio_stream_start', {
                        'messageId': message_id,
                        'room': room_id
                    }, room=room_id, namespace='/ws')
                    
                    chunk_number = 0
                    total_bytes_sent = 0
                    
                    print(f"🎤 Starting to stream audio with aiohttp: '{limited_text[:50]}...'")
                    
                    # Use OpenAI's official streaming approach with proper context management
                    async with async_client.audio.speech.with_streaming_response.create(
                        model=self.voice_config["model"],  # tts-1
                        voice=self.voice_config["voice"],  # echo
                        input=limited_text,
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
                                
                                # Log concise chunk info
                                print(f"🎵 Audio chunk {chunk_number} sent ({len(chunk)} bytes) to room {room_id}")
                                
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
                            print(f"🎵 Audio stream completed - {len(chunks_sent)} chunks sent ({total_bytes_sent} total bytes)")
                            
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
                        
                        print(f"✅ Streamed {chunk_number} PCM chunks ({total_bytes_sent} bytes) with aiohttp")
                    return True
                    
            except ImportError:
                # Fallback to default httpx if aiohttp is not available
                print("⚠️  aiohttp not available, falling back to default httpx")
                async with AsyncOpenAI(api_key=self.client.api_key) as async_client:
                    # Same streaming logic but with default httpx client
                    return await self._stream_with_client(async_client, text, room_id, message_id)
                    
            except Exception as e:
                print(f"Error generating streaming speech: {e}")
                # Signal error
                self.socketio.emit('ai_audio_error', {
                    'messageId': message_id,
                    'room': room_id,
                    'error': str(e)
                }, room=room_id, namespace='/ws')
                
                # Even on error, signal that audio streaming is done
                self.socketio.emit('ai_audio_done', {
                    'messageId': message_id,
                    'room': room_id,
                    'status': 'error'
                }, room=room_id, namespace='/ws')
                
                return None
        
        # Run the async function using asyncio.run in a safe way
        try:
            return asyncio.run(_async_generate_streaming())
        except Exception as e:
            print(f"Error in asyncio.run: {e}")
            # Fallback to simple non-streaming audio
            return self._fallback_simple_audio(text, room_id, message_id)
    
    def _fallback_simple_audio(self, text: str, room_id: str, message_id: str):
        """Fallback method for simple non-streaming audio generation"""
        try:
            # Limit text length
            limited_text = text[:500] + "..." if len(text) > 500 else text
            
            # Generate audio using the sync OpenAI client
            response = self.client.audio.speech.create(
                model=self.voice_config["model"],
                voice=self.voice_config["voice"],
                input=limited_text,
                speed=self.voice_config["speed"],
                response_format="mp3"
            )
            
            # Convert to base64 and send as single chunk
            audio_data = response.content
            chunk_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            print(f"🎵 MP3 audio generated ({len(audio_data)} bytes) for room {room_id}")
            
            # Send the complete audio as one chunk
            self.socketio.emit('ai_audio_chunk', {
                'messageId': message_id,
                'audioData': chunk_base64,
                'chunkNumber': 1,
                'totalBytes': len(audio_data),
                'room': room_id,
                'isComplete': True,
                'isRealtime': False,
                'format': 'mp3'
            }, room=room_id, namespace='/ws')

            # Signal completion
            self.socketio.emit('ai_audio_complete', {
                'messageId': message_id,
                'room': room_id,
                'totalChunks': 1,
                'totalBytes': len(audio_data),
                'format': 'mp3'
            }, room=room_id, namespace='/ws')
            
            print(f"✅ Generated MP3 audio ({len(audio_data)} bytes) for message {message_id}")
            return True
            
        except Exception as e:
            print(f"Error in fallback audio generation: {e}")
            return None

    def send_ai_message_with_audio(self, room_id: str, content: str, is_reflection: bool = False, 
                                       is_execution_help: bool = False, conversation_history=None):
        """Send an AI message to the chat room with audio - sync version"""
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
            'hasAudio': True,  # Will have audio
            'isStreaming': False  # Non-streaming in sync mode
        }
        
        # Update last response time for cooldown tracking
        if conversation_history and room_id in conversation_history:
            context = conversation_history[room_id]
            context.last_ai_response = datetime.now()
            print(f"🔒 AI RESPONSE: Tracking response time for cooldown in room {room_id}")
        
        print(f"🤖 Sending AI message with audio to room {room_id}: {content[:50]}...")
        
        # For personal rooms, extract user ID and send to specific user
        if "_personal_" in room_id:
            # Extract user ID from personal room ID: room123_personal_userID
            parts = room_id.split("_personal_")
            if len(parts) == 2:
                original_room = parts[0] 
                user_id = parts[1]
                print(f"🤖 Personal room detected - sending with audio to user {user_id} in original room {original_room}")
                
                # Update message room to original room for frontend display
                message['room'] = original_room
                
                # Send to specific user only
                self.socketio.emit('chat_message', message, room=user_id, namespace='/ws')
                
                # Generate audio for the personal user
                def generate_and_stream_audio():
                    try:
                        self.generate_streaming_speech(content, user_id, message['id'])  # Use user_id as target
                    except Exception as e:
                        print(f"Error in audio generation: {e}")
                        # Fallback to simple notification that audio failed
                        self.socketio.emit('ai_audio_error', {
                            'messageId': message['id'],
                            'room': original_room,
                            'error': 'Audio generation failed'
                        }, room=user_id, namespace='/ws')
                
                # Start audio generation in background thread
                threading.Thread(target=generate_and_stream_audio, daemon=True).start()
                return message
        
        # Regular shared room - send to all users in the room
        self.socketio.emit('chat_message', message, room=room_id, namespace='/ws')
        
        # Generate audio in parallel (non-blocking)
        def generate_and_stream_audio():
            try:
                self.generate_streaming_speech(content, room_id, message['id'])
            except Exception as e:
                print(f"Error in audio generation: {e}")
                # Fallback to simple notification that audio failed
                self.socketio.emit('ai_audio_error', {
                    'messageId': message['id'],
                    'room': room_id,
                    'error': 'Audio generation failed'
                }, room=room_id, namespace='/ws')
        
        # Start audio generation in a separate thread
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
        
        print(f"🤖 Sending text-only AI message to room {room_id}: {content[:50]}...")
        
        # For personal rooms, extract user ID and send to specific user
        if "_personal_" in room_id:
            # Extract user ID from personal room ID: room123_personal_userID
            parts = room_id.split("_personal_")
            if len(parts) == 2:
                original_room = parts[0] 
                user_id = parts[1]
                print(f"🤖 Personal room detected - sending to user {user_id} in original room {original_room}")
                
                # Update message room to original room for frontend display
                message['room'] = original_room
                
                # Send to specific user only
                self.socketio.emit('chat_message', message, room=user_id, namespace='/ws')
                return message
        
        # Regular shared room - send to all users in the room
        self.socketio.emit('chat_message', message, room=room_id, namespace='/ws')
        
        return message

    def send_ai_message(self, room_id: str, content: str, is_reflection: bool = False, 
                       is_execution_help: bool = False, conversation_history=None):
        """Send an AI message to the chat room (sync version)"""
        try:
            return self.send_ai_message_with_audio(
                room_id, content, is_reflection, is_execution_help, conversation_history)
        except Exception as e:
            # Fallback to simple text-only message
            print(f"Error sending AI message with audio, falling back to text: {e}")
            return self.send_ai_message_text_only(room_id, content, is_reflection, is_execution_help, conversation_history)

    def set_voice_config(self, voice: str = None, model: str = None, speed: float = None):
        """Update voice configuration for TTS"""
        if voice and voice in ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]:
            self.voice_config["voice"] = voice
        if model and model in ["tts-1", "tts-1-hd"]:
            self.voice_config["model"] = model
        if speed and 0.25 <= speed <= 4.0:
            self.voice_config["speed"] = speed

    async def _stream_with_client(self, async_client, text: str, room_id: str, message_id: str):
        """Helper method to handle streaming with any async client"""
        # Limit text length to avoid very long audio files
        limited_text = text[:500] + "..." if len(text) > 500 else text
        
        # Signal start of streaming
        self.socketio.emit('ai_audio_stream_start', {
            'messageId': message_id,
            'room': room_id
        }, room=room_id, namespace='/ws')
        
        chunk_number = 0
        total_bytes_sent = 0
        
        print(f"🎤 Starting to stream audio (fallback): '{limited_text[:50]}...'")
        
        # Use streaming approach with the provided client
        async with async_client.audio.speech.with_streaming_response.create(
            model=self.voice_config["model"],
            voice=self.voice_config["voice"],
            input=limited_text,
            speed=self.voice_config["speed"],
            response_format="pcm"
        ) as response:
            chunks_sent = []
            async for chunk in response.iter_bytes(chunk_size=1024 * 2):
                if chunk:
                    chunk_number += 1
                    total_bytes_sent += len(chunk)
                    chunk_base64 = base64.b64encode(chunk).decode('utf-8')
                    chunks_sent.append(chunk_number)
                    
                    self.socketio.emit('ai_audio_chunk', {
                        'messageId': message_id,
                        'audioData': chunk_base64,
                        'chunkNumber': chunk_number,
                        'totalBytes': total_bytes_sent,
                        'room': room_id,
                        'isComplete': False,
                        'isRealtime': True,
                        'format': 'pcm'
                    }, room=room_id, namespace='/ws')

            # Final marker
            if chunks_sent:
                final_chunk_number = chunks_sent[-1]
                self.socketio.emit('ai_audio_chunk', {
                    'messageId': message_id,
                    'audioData': '',
                    'chunkNumber': final_chunk_number,
                    'totalBytes': total_bytes_sent,
                    'room': room_id,
                    'isComplete': True,
                    'isRealtime': True,
                    'format': 'pcm',
                    'isFinalMarker': True
                }, room=room_id, namespace='/ws')

            # Signal completion
            self.socketio.emit('ai_audio_complete', {
                'messageId': message_id,
                'room': room_id,
                'totalChunks': chunk_number,
                'totalBytes': total_bytes_sent,
                'format': 'pcm'
            }, room=room_id, namespace='/ws')
            
            print(f"✅ Streamed {chunk_number} PCM chunks ({total_bytes_sent} bytes)")
        return True
