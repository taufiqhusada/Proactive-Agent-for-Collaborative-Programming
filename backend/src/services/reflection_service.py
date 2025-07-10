"""
Reflection Service - LLM-powered interactive learning reflection
Guides students through code understanding and learning consolidation
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
    def __init__(self, socketio_instance):
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
        
        # Send session started event with separator
        self.socketio.emit('reflection_started', {
            'session_id': session_id,
            'message': opening_message,
            'highlights': [],
            'separator': True,  # Indicates this starts a new reflection session
            'hasAudio': True  # Enable audio for opening message
        }, room=room_id, namespace='/ws')
        
        # Generate audio for the opening message
        print(f"🎓 About to generate audio for opening message: '{opening_message}'")
        self._generate_audio_for_message(opening_message, room_id)
        
        print(f"🎓 Started reflection session {session_id} for room {room_id}")
        return session_id
    
    def handle_reflection_response(self, session_id: str, user_message: str, user_info: Dict) -> bool:
        """Handle user response in reflection session with clean timer system"""
        print(f"🎓 handle_reflection_response called with session_id: {session_id}, message: '{user_message}', user: {user_info.get('username')}")
        
        if session_id not in self.active_sessions or not self.client:
            print(f"❌ Session {session_id} not found or no OpenAI client available")
            return False
            
        session = self.active_sessions[session_id]
        if not session.is_active:
            print(f"❌ Session {session_id} is not active")
            return False
        
        username = user_info.get('username', 'Student')
        room_id = session.room_id
        
        # Cancel any pending timer (new message received)
        self._cancel_pending_timer(room_id, "new message received")
        
        # Add user to active users list if not already there
        if username not in session.active_users:
            session.active_users.append(username)
        
        # Add user message to reflection history
        session.reflection_messages.append({
            'role': 'user',
            'content': user_message,
            'username': username,
            'timestamp': datetime.now().isoformat()
        })
        
        session.last_user_message_time = datetime.now()
        
        # Check for direct address - respond immediately
        if self._is_directly_addressed(user_message):
            print(f"🎓 Direct address detected - responding immediately")
            ai_response, highlights = self._generate_reflection_response(session)
            
            if ai_response:
                # Add AI message to history
                session.reflection_messages.append({
                    'role': 'assistant',
                    'content': ai_response,
                    'highlights': highlights,
                    'timestamp': datetime.now().isoformat()
                })
                
                # Update current highlights
                session.current_highlights = highlights
                
                # Send response to room
                self.socketio.emit('reflection_message', {
                    'session_id': session_id,
                    'message': ai_response,
                    'highlights': highlights,
                    'sender': 'ai',
                    'hasAudio': True
                }, room=room_id, namespace='/ws')
                
                # Generate audio for the response
                self._generate_audio_for_message(ai_response, room_id)
        else:
            # No direct address - start 5-second timer
            self._schedule_response_timer(room_id, session_id)
            
        return True
    
    def _is_directly_addressed(self, message: str) -> bool:
        """Check if the AI is directly addressed"""
        message_lower = message.lower().strip()
        ai_keywords = ['ai', 'bob', 'assistant']
        return any(keyword in message_lower for keyword in ai_keywords)
    
    def end_reflection_session(self, session_id: str) -> bool:
        """End reflection session"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.is_active = False
            
            final_message = "🎉 Great reflection session! You've learned a lot today. Keep up the excellent work!"
            
            # Send completion message
            self.socketio.emit('reflection_ended', {
                'session_id': session_id,
                'message': final_message,
                'summary': self._generate_session_summary(session),
                'hasAudio': True
            }, room=session.room_id, namespace='/ws')
            
            # Generate audio for final message
            self._generate_audio_for_message(final_message, session.room_id)
            
            print(f"🎓 Ended reflection session {session_id}")
            return True
        return False
    
    def end_reflection_session_by_room(self, room_id: str) -> bool:
        """End any active reflection session for a room (for user-initiated toggle off)"""
        session = self.get_active_reflection_session(room_id)
        if session:
            # Cancel any pending timers for this room
            self._cancel_pending_timer(room_id, "user ended reflection session")
            
            # Mark session as inactive
            session.is_active = False
            
            # Send a simple end message without ceremonial ending
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
    
    def update_session_code(self, room_id: str, current_code: str):
        """Update the current code for an active reflection session"""
        session = self.get_active_reflection_session(room_id)
        if session:
            session.final_code = current_code
            print(f"🎓 Updated reflection session code for room {room_id}")
    
    def _generate_reflection_response(self, session: ReflectionSession) -> Tuple[Optional[str], List[Dict]]:
        """Generate AI response with potential code highlights"""
        try:
            # Build conversation context
            conversation_history = []
            for msg in session.reflection_messages[-6:]:  # Last 6 messages for context
                conversation_history.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Add line numbers to code for highlighting
            code_with_lines = "\n".join([f"{i+1:2d}: {line}" for i, line in enumerate(session.final_code.split('\n'))])
            
            system_prompt = f"""You are a programming tutor helping with reflection. Be VERY concise - maximum 25 words total.

Current code with line numbers:
```{session.programming_language}
{code_with_lines}
```

Problem: {session.problem_description}

Ask ONE short question about what they learned or their approach. Use [HIGHLIGHT:start_line:end_line:description] to point to specific lines. Be encouraging but brief."""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt}
                ] + conversation_history,
                max_tokens=50,  # Much lower token limit
                temperature=0.6
            )
            
            ai_message = response.choices[0].message.content.strip()
            
            # Extract highlights from the message
            highlights = self._extract_highlights(ai_message, session.final_code)
            
            # Clean the message (remove highlight markers)
            clean_message = re.sub(r'\[HIGHLIGHT:\d+:\d+:[^\]]*\]', '', ai_message).strip()
            
            return clean_message, highlights
            
        except Exception as e:
            print(f"Error generating reflection response: {e}")
            return "Tell me more about your approach?", []
    
    def _extract_highlights(self, message: str, code: str) -> List[Dict]:
        """Extract code highlights from AI message"""
        highlights = []
        code_lines = code.split('\n')
        
        # Find highlight markers: [HIGHLIGHT:start_line:end_line:description]
        highlight_pattern = r'\[HIGHLIGHT:(\d+):(\d+):([^\]]*)\]'
        matches = re.findall(highlight_pattern, message)
        
        for match in matches:
            try:
                start_line = int(match[0])
                end_line = int(match[1])
                description = match[2]
                
                # Validate line numbers
                if 1 <= start_line <= len(code_lines) and 1 <= end_line <= len(code_lines):
                    highlights.append({
                        'start_line': start_line,
                        'end_line': end_line,
                        'description': description,
                        'type': 'question'
                    })
            except (ValueError, IndexError):
                continue
                
        return highlights
    
    def _generate_session_summary(self, session: ReflectionSession) -> Dict:
        """Generate a summary of the reflection session"""
        return {
            'duration_minutes': 5,  # Simplified
            'questions_discussed': len([msg for msg in session.reflection_messages if msg['role'] == 'assistant']),
            'code_sections_reviewed': len(session.current_highlights),
            'key_learnings': "Code understanding and problem-solving reflection"
        }
    
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
    
    def _schedule_response_timer(self, room_id: str, session_id: str):
        """Schedule a 5-second timer for reflection response"""
        import threading
        
        # Cancel existing timer
        self._cancel_pending_timer(room_id, "new timer scheduled")
        
        def timer_callback():
            """Handle timer completion after 5 seconds"""
            try:
                print(f"⏰ 5-second reflection timer completed for room {room_id}")
                
                # Clean up timer reference
                self.pending_timers.pop(room_id, None)
                
                # Generate AI response
                session = self.active_sessions.get(session_id)
                if session and session.is_active:
                    print(f"🎓 Generating AI response after 5-second delay")
                    ai_response, highlights = self._generate_reflection_response(session)
                    
                    if ai_response:
                        # Add AI message to history
                        session.reflection_messages.append({
                            'role': 'assistant',
                            'content': ai_response,
                            'highlights': highlights,
                            'timestamp': datetime.now().isoformat()
                        })
                        
                        # Update current highlights
                        session.current_highlights = highlights
                        
                        # Send response to room
                        self.socketio.emit('reflection_message', {
                            'session_id': session_id,
                            'message': ai_response,
                            'highlights': highlights,
                            'sender': 'ai',
                            'hasAudio': True
                        }, room=room_id, namespace='/ws')
                        
                        # Generate audio for the response
                        self._generate_audio_for_message(ai_response, room_id)
                else:
                    print(f"🚫 No reflection session found for timer completion in room {room_id}")
                        
            except Exception as e:
                print(f"❌ Reflection timer callback error for room {room_id}: {e}")
        
        # Create and start timer
        timer = threading.Timer(5.0, timer_callback)
        timer.daemon = True
        timer.start()
        
        # Store timer reference
        self.pending_timers[room_id] = timer
        print(f"⏱️ Started 5-second reflection timer for room {room_id}")

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
