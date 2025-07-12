"""
AI Intervention Service - Handles timer management and intervention scheduling
"""

import threading
import time
from datetime import datetime
from typing import Dict, Optional

from .ai_models import ConversationContext


class AIInterventionService:
    def __init__(self, ai_decision_callback, send_message_callback, get_conversation_history_callback):
        """
        Initialize intervention service
        
        Args:
            ai_decision_callback: Function to make AI intervention decisions
            send_message_callback: Function to send AI messages
            get_conversation_history_callback: Function to get conversation history
        """
        self.ai_decision_callback = ai_decision_callback
        self.send_message_callback = send_message_callback
        self.get_conversation_history_callback = get_conversation_history_callback
        
        # Simple timer tracking
        self.pending_timers: Dict[str, threading.Timer] = {}  # room_id -> threading.Timer
        
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
        # Cancel existing timer
        self._cancel_pending_intervention(room_id, "new timer scheduled")
        
        def timer_callback():
            """Handle timer completion after 5 seconds"""
            try:
                print(f"⏰ 5-second timer completed for room {room_id}")
                
                # Clean up timer reference
                self.pending_timers.pop(room_id, None)
                
                # Get conversation history through callback
                conversation_history = self.get_conversation_history_callback()
                
                # Check if we should respond
                if self.should_respond(room_id, conversation_history):
                    print(f"🤖 AI will respond after 5-second idle period in room {room_id}")
                    response = self._generate_response_sync(room_id)
                    if response:
                        self.send_message_callback(room_id, response)
                else:
                    print(f"🚫 No intervention needed after 5-second idle period for room {room_id}")
                        
            except Exception as e:
                print(f"❌ Timer callback error for room {room_id}: {e}")
        
        # Create and start timer
        timer = threading.Timer(5.0, timer_callback)
        timer.daemon = True
        timer.start()
        
        # Store timer reference
        self.pending_timers[room_id] = timer
        print(f"⏱️ Started 5-second timer for room {room_id}")

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
                
        # Need minimum number of messages
        if len(context.messages) < self.min_messages_before_response:
            print(f"🚫 AI WILL NOT RESPOND: Not enough messages ({len(context.messages)} < {self.min_messages_before_response})")
            return False
        
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
