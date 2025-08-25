"""
Reflection Service - LLM-powered interactive learning reflection
Combines AI agent reflection and dedicated reflection session logic
"""

import os
import json
import re
import time
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI
from dataclasses import dataclass

from .ai_models import ConversationContext

@dataclass
class ReflectionSession:
    session_id: str
    room_id: str
    final_code: str
    programming_language: str
    problem_description: str
    chat_history: List[Dict]
    reflection_messages: List[Dict]
    current_highlights: List[Dict]  # [{"start_line": 5, "end_line": 8, "type": "question"}]
    is_active: bool = False
    created_at: Optional[datetime] = None
    last_user_message_time: Optional[datetime] = None
    active_users: List[str] = None  # Track active users in conversation
    
    def __post_init__(self):
        if self.active_users is None:
            self.active_users = []

class ReflectionService:
    def __init__(self, socketio_instance=None):
        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("⚠️  Warning: No OpenAI API key found. Reflection will be disabled.")
            self.client = None
        else:
            try:
                self.client = OpenAI(api_key=api_key)
                print("✅ Reflection Service initialized successfully!")
            except Exception as e:
                print(f"❌ Error initializing OpenAI client: {e}")
                self.client = None
        
        self.socketio = socketio_instance
        self.active_sessions = {}  # session_id -> ReflectionSession
        self.pending_timers = {}   # room_id -> threading.Timer (like AI agent)
        
    def start_reflection_session(self, room_id: str, final_code: str, language: str, 
                               problem_description: str, chat_history: List[Dict]) -> str:
        """Start a new reflection session"""
        if not self.client:
            return None
            
        session_id = f"reflection_{room_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        session = ReflectionSession(
            session_id=session_id,
            room_id=room_id,
            final_code=final_code,
            programming_language=language,
            problem_description=problem_description,
            chat_history=chat_history[-20:],  # Last 20 messages for context
            reflection_messages=[],
            current_highlights=[],
            is_active=True,
            created_at=datetime.now()
        )
        
        self.active_sessions[session_id] = session
        
        # Use a simple static opening message instead of LLM generation
        opening_message = "What did you learn today?"
        
        # Send the message through the AI agent to ensure it's added to context
        self._send_reflection_message_via_ai_agent(room_id, opening_message, session_id, is_opening=True)
        
        print(f"🎓 Started reflection session {session_id} for room {room_id}")
        return session_id
    
    def end_reflection_session_by_room(self, room_id: str) -> bool:
        """End any active reflection session for a room (for user-initiated toggle off)"""
        session = self.get_active_reflection_session(room_id)
        if session:
            # Cancel any pending timers for this room
            self._cancel_pending_timer(room_id, "user ended reflection session")
            
            # Mark session as inactive
            session.is_active = False
            
            # Send a simple end message without ceremonial ending
            if self.socketio:
                self.socketio.emit('reflection_ended', {
                    'session_id': session.session_id,
                    'message': 'Reflection session ended. Back to regular coding assistance!',
                    'summary': None,  # No summary for user-initiated end
                    'hasAudio': False,  # No audio for quick toggle
                    'user_initiated': True  # Flag to indicate user ended it
                }, room=room_id, namespace='/ws')
            
            print(f"🎓 User ended reflection session {session.session_id} for room {room_id}")
            return True
        return False
    
    def is_room_in_reflection(self, room_id: str) -> bool:
        """Check if a room currently has an active reflection session"""
        for session in self.active_sessions.values():
            if session.room_id == room_id and session.is_active:
                return True
        return False
    
    def get_active_reflection_session(self, room_id: str) -> Optional[ReflectionSession]:
        """Get the active reflection session for a room, if any"""
        for session in self.active_sessions.values():
            if session.room_id == room_id and session.is_active:
                return session
        return None

    def generate_reflection_response_sync(self, room_id: str, conversation_history) -> Optional[str]:
        """Generate a reflection response synchronously"""
        try:
            if not self.client:
                print("⚠️  Cannot generate reflection response: OpenAI client not initialized")
                return "What did you find challenging?"
            
            context = conversation_history.get(room_id)
            if not context:
                return "What did you learn today?"
            
            # Get current code from context
            current_code = context.code_context
            language = context.programming_language
            
            print(f"🎓 DEBUG: Reflection prompt code context: '{current_code[:100] if current_code else 'EMPTY'}'")
            print(f"🎓 DEBUG: Language: '{language}'")
            
            # Create reflection prompt
            reflection_prompt = self._create_reflection_prompt(context, current_code, language)
            print(f"🎓 Reflection prompt: {reflection_prompt}")
            
            # Generate response using OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You are a supportive programming tutor. Keep responses very short (1-2 sentences max). Ask simple, focused questions to help students reflect."},
                    {"role": "user", "content": reflection_prompt}
                ],
                max_tokens=50,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"❌ Error generating reflection response: {e}")
            return "What was the trickiest part?"

    def _create_reflection_prompt(self, context: ConversationContext, current_code: str, language: str) -> str:
        """Create a reflection-specific prompt"""
        recent_messages = context.messages[-5:] if context.messages else []
        print(f"🎓 DEBUG: Recent messages for reflection: {recent_messages}")
        
        # Build conversation including both user and AI messages, but exclude system messages
        conversation_lines = []
        for msg in recent_messages:
            if not msg.content.startswith("🎓"):  # Skip system reflection messages
                conversation_lines.append(f"{msg.username}: {msg.content}")
        
        conversation = "\n".join(conversation_lines)
        
        # Include problem context if available
        problem_section = ""
        if context.problem_description or context.problem_title:
            problem_text = context.problem_description or context.problem_title
            problem_section = f"""Problem: {problem_text}"""
        
        return f"""You are a supportive programming tutor helping students reflect on their learning and deepen their understanding. Keep responses very short and focused.

                    {problem_section}Current code:
                    ```{language}
                    {current_code}
                    ```

                    Follow this progression for reflection questions (1-2 sentences max):

                    PRIORITY 1 - Code Understanding (start here):
                    - "How does [specific part of their code] work?"
                    - "What's this function doing?"
                    - "Can you walk me through this logic?"

                    PRIORITY 2 - Once they show understanding, explore deeper:
                    - Algorithm concepts: "What's the time complexity of your approach?"
                    - Alternatives: "Can you think of a different way to solve this?"
                    - Improvements: "How might you optimize this code?"
                    - Edge cases: "What if the input was empty/negative/huge?"

                    If they ask for help or seem stuck, provide brief guidance instead of asking questions.

                    Recent conversation:
                    {conversation}

                    IMPORTANT: Review the conversation above. Do NOT repeat any question you've already asked. If the student has already answered a question, move on to the next one. Build on what they've shared.

                    Response:"""

    def send_reflection_opening(self, room_id: str, send_message_callback):
        """Send the opening reflection question immediately"""
        try:
            opening_message = "What did you learn today?"
            send_message_callback(room_id, opening_message, is_reflection=True)
            print(f"🎓 Sent reflection opening message to room {room_id}")
        except Exception as e:
            print(f"❌ Error sending reflection opening: {e}")
    
    def _generate_audio_for_message(self, message: str, room_id: str):
        """Generate audio for reflection messages using OpenAI TTS with streaming pattern"""
        print(f"🎓 _generate_audio_for_message called with message: '{message}' for room: {room_id}")
        
        try:
            if not self.client:
                print("❌ No OpenAI client available for audio generation")
                return
                
            # Generate unique message ID for this reflection audio
            message_id = f"reflection_{int(time.time() * 1000)}"
            print(f"🎓 Generated message ID: {message_id}")
            
            # Generate TTS audio
            print(f"🎓 Calling OpenAI TTS API...")
            response = self.client.audio.speech.create(
                model="tts-1",
                voice="echo",  # Same voice as regular AI agent
                input=message,
                response_format="mp3",
                speed=1.0
            )
            
            # Get audio data
            audio_data = response.content
            print(f"🎓 Received audio data: {len(audio_data)} bytes")
            
            # Send audio using the same streaming pattern as AI agent
            # Start streaming
            print(f"🎓 Sending ai_audio_stream_start event...")
            self.socketio.emit('ai_audio_stream_start', {
                'messageId': message_id,
                'room': room_id,
                'totalChunks': 1,  # Single chunk for reflection
                'isReflection': True
            }, room=room_id, namespace='/ws')
            
            # Send the audio chunk
            print(f"🎓 Sending ai_audio_chunk event...")
            self.socketio.emit('ai_audio_chunk', {
                'messageId': message_id,
                'chunkNumber': 0,  # Use chunkNumber not chunkIndex
                'audioData': base64.b64encode(audio_data).decode('utf-8'),  # Convert to base64 for transport
                'totalBytes': len(audio_data),
                'room': room_id,
                'isComplete': True,  # This is the only chunk
                'isRealtime': False,  # Pre-generated audio
                'format': 'mp3',  # MP3 format
                'isReflection': True
            }, room=room_id, namespace='/ws')
            
            # Complete streaming
            print(f"🎓 Sending ai_audio_complete event...")
            self.socketio.emit('ai_audio_complete', {
                'messageId': message_id,
                'room': room_id,
                'totalChunks': 1,
                'isReflection': True
            }, room=room_id, namespace='/ws')
            
            print(f"🎓 Successfully generated and sent reflection audio for message: {message[:50]}...")
            
        except Exception as e:
            print(f"❌ Error generating reflection audio: {e}")
            # Send error event
            if self.socketio:
                self.socketio.emit('ai_audio_error', {
                    'messageId': f"reflection_{int(time.time() * 1000)}",
                    'room': room_id,
                    'error': str(e),
                    'isReflection': True
                }, room=room_id, namespace='/ws')
    
    def _cancel_pending_timer(self, room_id: str, reason: str):
        """Cancel any pending timer for a room"""
        print(f"🔍 CANCEL TIMER called for room {room_id}, reason: {reason}")
        print(f"🔍 Pending timers: {list(self.pending_timers.keys())}")
        
        if room_id in self.pending_timers:
            timer = self.pending_timers[room_id]
            timer.cancel()
            del self.pending_timers[room_id]
            print(f"🚫 CANCELLED reflection timer ({reason}) in room {room_id}")
        else:
            print(f"⚠️ No pending timer found for room {room_id} to cancel")
    
    def _add_reflection_message_to_ai_context(self, room_id: str, message_content: str):
        """Add reflection message to AI agent context for conversation tracking"""
        try:
            # Import here to avoid circular imports
            from .ai_agent import get_ai_agent
            ai_agent = get_ai_agent()
            
            if ai_agent:
                # Create a message structure similar to what users send
                message_data = {
                    'id': f"reflection_{int(time.time() * 1000)}",
                    'content': f"🎓 {message_content}",  # Mark as reflection with emoji
                    'username': 'AI Reflection',
                    'userId': 'ai_reflection',
                    'timestamp': datetime.now().isoformat(),
                    'room': room_id,
                    'isAutoGenerated': True
                }
                
                # Add to AI agent's conversation context
                ai_agent.add_message_to_context(message_data)
                print(f"🎓 Added reflection message to AI context: {message_content[:50]}...")
            else:
                print("⚠️ Could not add reflection message to AI context: AI agent not available")
        except Exception as e:
            print(f"❌ Error adding reflection message to AI context: {e}")
    
    def _send_reflection_message_via_ai_agent(self, room_id: str, message: str, session_id: str = None, is_opening: bool = False):
        """Send reflection message through AI agent to ensure proper context tracking"""
        try:
            from .ai_agent import get_ai_agent
            ai_agent = get_ai_agent()
            
            if ai_agent:
                # Use the AI agent's send_ai_message method which includes context addition
                ai_agent.send_ai_message(room_id, message, is_reflection=True)
                
                print(f"🎓 Sent reflection message via AI agent and added to context: {message[:50]}...")
            else:
                print("⚠️ Could not send reflection message: AI agent not available")
                # Fallback to direct socketio if AI agent unavailable
                if self.socketio:
                    self.socketio.emit('reflection_message', {
                        'session_id': session_id or 'unknown',
                        'message': message,
                        'highlights': [],
                        'sender': 'ai',
                        'hasAudio': True
                    }, room=room_id, namespace='/ws')
        except Exception as e:
            print(f"❌ Error sending reflection message via AI agent: {e}")

# Legacy class alias for backward compatibility
AIReflectionService = ReflectionService

# Global instance
reflection_service = None

def init_reflection_service(socketio_instance):
    """Initialize the reflection service"""
    global reflection_service
    reflection_service = ReflectionService(socketio_instance)
    return reflection_service

def get_reflection_service():
    """Get the reflection service instance"""
    return reflection_service
