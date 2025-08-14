"""
AI Intervention Service - Handles timer management and intervention scheduling
"""

import asyncio
import threading
import time
from datetime import datetime
from typing import Dict, Optional

from .ai_models import ConversationContext


class AIInterventionService:
    def __init__(self, ai_decision_callback, send_message_callback, get_conversation_history_callback, send_progress_notification_callback=None):
        """
        Initialize intervention service
        
        Args:
            ai_decision_callback: Function to make AI intervention decisions
            send_message_callback: Function to send AI messages
            get_conversation_history_callback: Function to get conversation history
            send_progress_notification_callback: Function to send progress check notifications (optional, defaults to send_message_callback)
        """
        self.ai_decision_callback = ai_decision_callback
        self.send_message_callback = send_message_callback
        self.send_progress_notification_callback = send_progress_notification_callback or send_message_callback
        self.get_conversation_history_callback = get_conversation_history_callback
        
        # Simple timer tracking
        self.pending_timers: Dict[str, threading.Timer] = {}  # room_id -> threading.Timer
        
        # Progress tracking - single 30s timer per room
        self.progress_timers: Dict[str, threading.Timer] = {}  # room_id -> threading.Timer
        
        # Intervention configuration settings
        self.intervention_settings = {
            'idle_intervention_enabled': True,  # idle intervention
            'idle_intervention_delay': 5,       # seconds to wait before idle intervention
            'progress_check_enabled': True,     # progress check
            'progress_check_interval': 45       # seconds between progress checks
        }
        
        # Timing parameters
        self.response_cooldown = 15  # Minimum seconds between AI responses
        self.min_messages_before_response = 3  # Wait for at least 3 messages before responding

    def _cancel_pending_intervention(self, room_id: str, reason: str):
        """Cancel any pending timer for a room"""
        if room_id in self.pending_timers:
            timer = self.pending_timers[room_id]
            timer.cancel()
            del self.pending_timers[room_id]
            print(f"🚫 CANCELLED timer ({reason}) in room {room_id}")
    
    def _schedule_idle_intervention(self, room_id: str):
        """Schedule a 5-second idle intervention timer using threading.Timer"""
        # Check if idle intervention is disabled
        if not self.intervention_settings.get('idle_intervention_enabled', True):
            print(f"🚫 Idle intervention disabled for room {room_id}")
            return
            
        # Cancel existing timer
        self._cancel_pending_intervention(room_id, "new timer scheduled")
        
        def timer_callback():
            """Handle timer completion after configured delay"""
            try:
                delay = self.intervention_settings.get('idle_intervention_delay', 5)
                print(f"⏰ {delay}-second timer completed for room {room_id}")
                
                # Clean up timer reference
                self.pending_timers.pop(room_id, None)
                
                # Get conversation history through callback
                conversation_history = self.get_conversation_history_callback()
                
                # Check if we should respond
                if self.should_respond(room_id, conversation_history):
                    print(f"🤖 AI will respond after {delay}-second idle period in room {room_id}")
                    response = self._generate_response_sync(room_id)
                    if response:
                        self.send_message_callback(room_id, response)
                else:
                    print(f"🚫 No intervention needed after {delay}-second idle period for room {room_id}")
                        
            except Exception as e:
                print(f"❌ Timer callback error for room {room_id}: {e}")
        
        # Create and start timer with configurable delay
        delay = self.intervention_settings.get('idle_intervention_delay', 5)
        timer = threading.Timer(float(delay), timer_callback)
        timer.daemon = True
        timer.start()
        
        # Store timer reference
        self.pending_timers[room_id] = timer
        print(f"⏱️ Started {delay}-second timer for room {room_id}")

    def _schedule_reflection_response(self, room_id: str):
        """Schedule a reflection response after 5 seconds"""
        # Cancel any existing timer
        self._cancel_pending_intervention(room_id, "new reflection message")
        
        # Start new 5-second timer for reflection
        timer = threading.Timer(5.0, self._send_reflection_response, args=[room_id])
        self.pending_timers[room_id] = timer
        timer.start()
        print(f"🎓 Scheduled reflection response in 5 seconds for room {room_id}")

    def _send_reflection_response(self, room_id: str):
        """Send a reflection-specific AI response"""
        try:
            print(f"🎓 Generating reflection response for room {room_id}")
            
            # Generate response using the callback (returns tuple: should_respond, message)
            should_respond, ai_message = self.ai_decision_callback(room_id, is_reflection=True)
            
            if should_respond and ai_message:
                # Send as reflection message (use only the message part, not the tuple)
                self.send_message_callback(room_id, ai_message, is_reflection=True)
                print(f"🎓 Sent reflection response to room {room_id}")
            else:
                print(f"❌ Failed to generate reflection response for room {room_id}")
            
            # Clean up timer
            if room_id in self.pending_timers:
                del self.pending_timers[room_id]
                
        except Exception as e:
            print(f"❌ Error sending reflection response: {e}")

    def _generate_response_sync(self, room_id: str) -> Optional[str]:
        """Synchronous response generation for timer callbacks"""
        try:
            should_intervene, message = self.ai_decision_callback(room_id)
            
            if should_intervene:
                print(f"✅ Generated response: {message[:50]}...")
                return message
            return None
        except Exception as e:
            print(f"❌ Error in response generation: {e}")
            return None

    def should_respond(self, room_id: str, conversation_history: Dict[str, ConversationContext]) -> bool:
        """Simple decision making for AI intervention after 5-second idle"""
        # Check if room is in reflection mode - if so, skip normal AI responses
        try:
            from .ai_reflection import get_reflection_service
            reflection_service = get_reflection_service()
            if reflection_service and reflection_service.is_room_in_reflection(room_id):
                print(f"🎓 AI WILL NOT RESPOND: Room {room_id} is in reflection mode")
                return False
        except:
            pass  # Continue if reflection service not available
            
        if room_id not in conversation_history:
            print(f"🚫 AI WILL NOT RESPOND: No conversation history for room {room_id}")
            return False
            
        context = conversation_history[room_id]

        # Check cooldown period
        if context.last_ai_response:
            time_since_last = datetime.now() - context.last_ai_response
            if time_since_last.total_seconds() < self.response_cooldown:
                print(f"🚫 AI WILL NOT RESPOND: Cooldown period ({time_since_last.total_seconds():.1f}s < {self.response_cooldown}s)")
                return False
                
        # # Need minimum number of messages
        # if len(context.messages) < self.min_messages_before_response:
        #     print(f"🚫 AI WILL NOT RESPOND: Not enough messages ({len(context.messages)} < {self.min_messages_before_response})")
        #     return False
        
        # Simple AI decision using centralized LLM
        should_intervene, intervention_message = self.ai_decision_callback(room_id)
        
        if should_intervene:
            print(f"✅ AI WILL RESPOND: Intervention decision made for room {room_id}")
            # Store the intervention message for generate_response to use
            context.pending_intervention_message = intervention_message
        else:
            print(f"🚫 AI WILL NOT RESPOND: AI decided not to intervene for room {room_id}")
        
        return should_intervene

    def cancel_intervention(self, room_id: str, reason: str):
        """Public method to cancel pending interventions"""
        self._cancel_pending_intervention(room_id, reason)

    def schedule_idle_intervention(self, room_id: str):
        """Public method to schedule idle intervention"""
        self._schedule_idle_intervention(room_id)

    def schedule_reflection_response(self, room_id: str):
        """Public method to schedule reflection response"""
        self._schedule_reflection_response(room_id)

    def has_pending_timer(self, room_id: str) -> bool:
        """Check if room has a pending timer"""
        return room_id in self.pending_timers

    def cleanup_room(self, room_id: str):
        """Clean up all timers for a room"""
        self._cancel_pending_intervention(room_id, "room cleanup")
        self._cancel_progress_timer(room_id, "room cleanup")
    
    # Progress tracking methods
    def trigger_progress_check(self, room_id: str):
        """Trigger (45)-second progress check timer on new message"""
        # Check if progress check is disabled
        if not self.intervention_settings.get('progress_check_enabled', True):
            print(f"🚫 Progress check disabled for room {room_id}")
            return
            
        # If already running, don't create new timer
        if room_id in self.progress_timers:
            print(f"📊 Progress timer already running for room {room_id}, keeping existing")
            return
            
        interval = self.intervention_settings.get('progress_check_interval', 45)
        print(f"📊 Starting {interval}-second progress check timer for room {room_id}")
        
        def progress_check_callback():
            """Handle progress check"""
            try:
                print(f"📊 {interval}-second progress check triggered for room {room_id}")
                
                # Clean up timer reference
                self.progress_timers.pop(room_id, None)
                
                # Get conversation history
                conversation_history = self.get_conversation_history_callback()
                context = conversation_history.get(room_id)
                
                if not context or len(context.messages) < 3:
                    print(f"📊 Progress check skipped for room {room_id}: Not enough activity")
                    return
                
                # Use specialized AI decision for progress tracking
                should_intervene, message = self.ai_decision_callback(room_id, is_progress_check=True)
                
                if should_intervene and message:
                    print(f"📊 Progress intervention needed for room {room_id}: {message[:50]}...")
                    # Use the progress notification callback instead of regular message callback
                    self.send_progress_notification_callback(room_id, message)
                else:
                    print(f"📊 Progress check: Users on track in room {room_id}")
                    
            except Exception as e:
                print(f"❌ Error in progress check for room {room_id}: {e}")
        
        # Create and start timer with configurable interval
        timer = threading.Timer(float(interval), progress_check_callback)
        timer.daemon = True
        timer.start()
        
        # Store timer reference
        self.progress_timers[room_id] = timer
    
    def _cancel_progress_timer(self, room_id: str, reason: str):
        """Cancel any pending progress timer for a room"""
        if room_id in self.progress_timers:
            timer = self.progress_timers[room_id]
            timer.cancel()
            del self.progress_timers[room_id]
            print(f"🚫 CANCELLED progress timer ({reason}) in room {room_id}")
    
    def cancel_progress_check(self, room_id: str, reason: str):
        """Public method to cancel progress check""" 
        self._cancel_progress_timer(room_id, reason)
    
    def has_progress_timer(self, room_id: str) -> bool:
        """Check if room has a pending progress timer"""
        return room_id in self.progress_timers
    
    def get_active_progress_rooms(self):
        """Get list of rooms with active progress timers"""
        return list(self.progress_timers.keys())

    def update_intervention_settings(self, settings: Dict[str, bool]):
        """Update intervention configuration settings"""
        for key, value in settings.items():
            if key in self.intervention_settings:
                self.intervention_settings[key] = value
                print(f"🔧 Updated intervention setting: {key} = {value}")
        
        # If idle intervention is disabled, cancel all pending timers
        if not self.intervention_settings.get('idle_intervention_enabled', True):
            for room_id in list(self.pending_timers.keys()):
                self._cancel_pending_intervention(room_id, "idle intervention disabled")
        
        # If progress check is disabled, cancel all progress timers
        if not self.intervention_settings.get('progress_check_enabled', True):
            for room_id in list(self.progress_timers.keys()):
                self._cancel_progress_timer(room_id, "progress check disabled")
    
    def get_intervention_settings(self) -> Dict[str, bool]:
        """Get current intervention configuration settings"""
        return self.intervention_settings.copy()
