"""
AI Agent Core - Main AIAgent class with core functionality
Simplified and modular design using specialized service classes
"""

import os
import random
import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from openai import OpenAI

from .ai_models import Message, ConversationContext
from .ai_audio import AIAudioService
from .ai_intervention import AIInterventionService
from .ai_code_analysis import AICodeAnalysisService
from .ai_reflection import get_reflection_service


class AIAgent:
    def __init__(self, socketio_instance):
        # Check if OpenAI API key is available
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("⚠️  Warning: No OpenAI API key found. AI agent will be disabled.")
            print("   Set OPENAI_API_KEY in your .env file to enable AI responses.")
            self.client = None
        else:
            try:
                self.client = OpenAI(api_key=api_key)
                print("✅ AI Agent (Bob) initialized successfully!")
            except Exception as e:
                print(f"❌ Error initializing OpenAI client: {e}")
                print("   AI agent will be disabled.")
                self.client = None
        
        self.socketio = socketio_instance
        self.conversation_history = {}  # room_id -> ConversationContext
        
        # AI Agent identity
        self.agent_name = "Bob (AI Assistant)"
        self.agent_id = "ai_agent_bob"
        
        # Initialize specialized services
        self.audio_service = AIAudioService(
            socketio_instance, self.client, self.agent_name, self.agent_id
        )
        
        self.intervention_service = AIInterventionService(
            ai_decision_callback=self._centralized_ai_decision,
            send_message_callback=self.send_ai_message,
            get_conversation_history_callback=lambda: self.conversation_history
        )
        
        self.code_analysis_service = AICodeAnalysisService(
            self.client, socketio_instance
        )
        
        # Reflection service will be obtained when needed (it may not be initialized yet)
        self.reflection_service = None

    def _centralized_ai_decision(self, room_id: str, is_reflection: bool = False, is_progress_check: bool = False) -> tuple[bool, str]:
        """Central AI decision making: Should intervene and what to say"""
        if not self.client:
            print("🚫 AI WILL NOT INTERVENE: No LLM client available")
            return False, ""
        
        context = self.conversation_history.get(room_id)
        if not context:
            return False, ""

        # Handle reflection mode
        if is_reflection:
            # Get reflection service dynamically (it may not have been initialized during __init__)
            if not self.reflection_service:
                self.reflection_service = get_reflection_service()
            
            if self.reflection_service:
                response = self.reflection_service.generate_reflection_response_sync(
                    room_id, self.conversation_history
                )
            else:
                print("❌ Error: Reflection service not available")
                response = "What did you learn today?"
            return True, response if response else "What did you learn today?"
        
        # Handle 30-second progress check
        if is_progress_check:
            return self._handle_progress_check(room_id, context)

        # Get recent conversation context (last 5 messages)
        recent_conversation = ""
        for msg in context.messages[-5:]:
            recent_conversation += f"{msg.username}: {msg.content}\n"
        
        # Check if the last message contains direct AI mention
        last_message = context.messages[-1] if context.messages else None
        is_direct_mention = last_message and self._is_direct_ai_mention(last_message.content)
        
        # Check if user is asking for syntax/code
        is_syntax_request = last_message and self._is_syntax_request(last_message.content)
        
        # Build AI message history context to avoid repetition
        ai_history_context = self._build_ai_history_context(context)
        
        # Add special syntax request guidance
        if is_syntax_request:
            ai_history_context += "\n\n🚨 SYNTAX REQUEST DETECTED: User is asking for actual code/syntax. PROVIDE CONCRETE CODE EXAMPLES!"
        
        # Adjust prompt based on whether this is a direct mention
        if is_direct_mention:
            prompt = f"""You are Bob, an AI pair programming assistant focused on LEARNING. The user has directly mentioned you with @AI or similar keyword.

                            Problem Context:
                            - Problem title: {context.problem_title or "General coding"}
                            - Problem description: {context.problem_description or "No specific problem"}
                            - Language: {context.programming_language}

                            Recent Conversation (FOCUS ON LAST MESSAGE):
                            {recent_conversation}

                            Code Context:
                            {context.code_context if context.code_context else "No code visible"}

                            {ai_history_context}

                            PROGRESSIVE LEARNING APPROACH - Help users learn step by step:
                            - CRITICAL: Look at your recent messages above - you CANNOT repeat the same type of response
                            - If you've already asked questions, DON'T ask more questions - give concrete answers
                            - If you've given general hints, provide SPECIFIC details or examples
                            - When they say "I don't know" repeatedly - they need concrete help, NOT more questions
                            - FOLLOW THE GUIDANCE LEVEL: Each message must be more concrete than the previous
                            - Balance learning with being actually helpful - don't leave them completely stuck

                            Response format:
                            - If you should help: "YES|[MUST be different from your previous messages - be more concrete - 15-50 words]"
                            - If inappropriate request: "NO"

                            REMEMBER: DO NOT repeat your previous approach - if you asked questions before, give concrete answers now!

                            Your response:"""
        else:
            prompt = f"""You are Bob, an AI pair programming assistant focused on LEARNING. Should you help in this conversation?

                        Problem Context:
                        - Problem title: {context.problem_title or "General coding"}
                        - Problem description: {context.problem_description or "No specific problem"}
                        - Language: {context.programming_language}

                        Recent Conversation:
                        {recent_conversation}

                        Code Context:
                        {context.code_context if context.code_context else "No code visible"}

                        {ai_history_context}

                        PROGRESSIVE INTERVENTION - Guide learning appropriately:
                        - CRITICAL: Look at your recent messages above - you CANNOT give the same type of response again
                        - If you've asked questions before, DON'T ask more questions - provide specific answers
                        - If you gave general hints before, give CONCRETE examples or show actual code
                        - When they say "I don't know" repeatedly: They need specific help, NOT more questions
                        - If they're discussing actively: Let them work it out
                        - If they need encouragement: Give positive reinforcement  
                        - FOLLOW THE GUIDANCE LEVEL: Each response must be MORE CONCRETE than your previous ones
                        Response format:
                        - If you should help: "YES|[MUST be different from previous messages - escalate to more concrete - 10-40 words]"  
                        - If they're doing fine: "NO"

                        CRITICAL: DO NOT repeat your previous approach - if you gave questions before, give concrete examples now!

                        Your response:"""
            

        print("🔍 AI Decision prompt:", prompt, "...")  # Log first 200 chars for debugging

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are Bob, a learning-focused pair programming assistant. Provide progressive hints and guidance to help users learn, not complete solutions. Start with conceptual hints, then provide syntax hints only when specifically requested, and avoid giving full solutions unless users are completely stuck."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150 if is_direct_mention else 100,
                temperature=0.7
            )
            
            llm_response = response.choices[0].message.content.strip()
            
            if llm_response.startswith("YES|"):
                # Parse the response: YES|MESSAGE
                parts = llm_response.split("|", 1)
                if len(parts) >= 2:
                    intervention_message = parts[1]
                    
                    mention_type = "DIRECT MENTION" if is_direct_mention else "IDLE INTERVENTION"
                    print(f"✅ AI WILL INTERVENE ({mention_type}): {intervention_message[:50]}...")
                    return True, intervention_message
                else:
                    print(f"❌ LLM response format error: {llm_response}")
                    return False, ""
            else:
                mention_type = "direct mention" if is_direct_mention else "idle period"
                print(f"🚫 AI WILL NOT INTERVENE: Decided not to respond to {mention_type}")
                return False, ""
                
        except Exception as e:
            print(f"❌ Error in AI decision: {e}")
            return False, ""

    def _handle_progress_check(self, room_id: str, context: ConversationContext) -> tuple[bool, str]:
        """Handle 30-second progress check intervention"""
        try:
            # Build conversation context (last 8 messages for better context)
            recent_conversation = ""
            for msg in context.messages[-10:]:
                recent_conversation += f"{msg.username}: {msg.content}\n"
            
            # Build current state context
            current_code = context.code_context if context.code_context else "No code written yet"
            problem_info = f"Title: {context.problem_title or 'Not specified'}\nDescription: {context.problem_description or 'Not specified'}"
            
            # Build AI message history context to avoid repetition
            ai_history_context = self._build_ai_history_context(context)
            
            # Create progress check prompt
            prompt = f"""You are Bob, an AI pair programming assistant. You're doing a 30-second progress check to see if users are on track.

Problem Context:
{problem_info}
Language: {context.programming_language}

Current Code:
{current_code}

Recent Conversation (last 10 messages):
{recent_conversation}

{ai_history_context}

PROGRESS CHECK TASK:
Analyze if the users are making good progress toward solving the problem. Look for:

RED FLAGS (should intervene):
- Discussing completely wrong approach
- Stuck on same issue repeatedly 
- Silent for too long while having an active problem
- Code going in wrong direction vs problem requirements
- Misunderstanding fundamental concepts
- One person dominating, other not participating

GREEN FLAGS (don't intervene):
- Making steady progress, even if slow
- Having productive discussions about approach
- Recently made progress or breakthroughs  
- Actively debugging and learning
- Both people contributing to conversation
- On right track even if minor issues

CRITICAL: Check your recent AI messages above - do NOT repeat the same intervention!
- If you've already given basic hints, provide more specific guidance
- If you've given specific tips, try a different approach or escalate to solution steps
- Vary your intervention type and content based on what you've said before

INTERVENTION TYPES:
- REDIRECT: "I notice you're discussing X, but for this problem you might want to consider Y instead. What do you think?"
- ENCOURAGE: "You're on the right track! Consider focusing on [specific next step]."
- FACILITATE: "What does your partner think about this approach?" or "Can you explain your idea to your partner?"
- HINT: "For this type of problem, you might want to think about [specific concept/approach]."

Response format:
- If should intervene: "YES|[intervention type]|[helpful message 15-40 words]"
- If making good progress: "NO|[reason why they're doing well 10-30 words]"

Your response:"""
            

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful pair programming assistant doing progress monitoring. Only intervene when users truly need guidance."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=120,
                temperature=0.7
            )
            
            llm_response = response.choices[0].message.content.strip()
            print(f"📊 Progress check LLM response: {llm_response}")
            
            if llm_response.startswith("YES|"):
                # Parse: YES|TYPE|MESSAGE
                parts = llm_response.split("|", 2)
                if len(parts) >= 3:
                    intervention_type = parts[1]
                    intervention_message = parts[2]
                    
                    print(f"📊 PROGRESS INTERVENTION ({intervention_type}): {intervention_message[:50]}...")
                    return True, intervention_message
                else:
                    print(f"❌ Progress check format error: {llm_response}")
                    return False, ""
            elif llm_response.startswith("NO|"):
                # Parse: NO|REASON
                parts = llm_response.split("|", 1)
                if len(parts) >= 2:
                    reason = parts[1]
                    print(f"📊 Progress check: Users making good progress in room {room_id} - Reason: {reason}")
                    return False, ""
                else:
                    print(f"📊 Progress check: Users making good progress in room {room_id}")
                    return False, ""
            else:
                print(f"📊 Progress check: Users making good progress in room {room_id}")
                return False, ""
                
        except Exception as e:
            print(f"❌ Error in progress check: {e}")
            return False, ""

    def _is_direct_ai_mention(self, message_content: str) -> bool:
        """Check if message contains direct AI mention keywords"""
        # Split into words for exact word matching (more efficient and accurate)
        words = message_content.lower().split()
        
        # Single-word AI mention keywords
        ai_keywords = {
            '@ai', '@bob', 'bob', 'hey bob'
        }
        
        # Check if any word is an AI keyword
        return any(word in ai_keywords for word in words)

    def _is_syntax_request(self, message_content: str) -> bool:
        """Check if message contains syntax request keywords"""
        content_lower = message_content.lower()
        
        syntax_keywords = [
            'syntax', 'code', 'show me', 'give me', 'how do i', 'how to',
            'what is the', 'can you write', 'example', 'sample'
        ]
        
        return any(keyword in content_lower for keyword in syntax_keywords)

    def _build_ai_history_context(self, context: ConversationContext) -> str:
        """Build context about recent AI messages to avoid repetition"""
        print(f"🔍 Building AI history context. Messages in history: {len(context.ai_message_history)}")
        for i, msg in enumerate(context.ai_message_history):
            print(f"   {i+1}. {msg[:50]}...")
            
        if not context.ai_message_history:
            return "REPETITION CHECK: No recent AI messages - this is your first intervention in a while."
            return "REPETITION CHECK: No recent AI messages - this is your first intervention in a while."
        
        recent_ai_messages = context.ai_message_history[-5:]  # Last 5 AI messages
        ai_context = "REPETITION CHECK - Your Recent AI Messages (AVOID REPEATING):\n"
        for i, msg in enumerate(recent_ai_messages, 1):
            ai_context += f"  {i}. \"{msg}\"\n"
        
        # Give progressive guidance based on message count
        # message_count = len(context.ai_message_history)
        # if message_count == 0:
        #     ai_context += "GUIDANCE: First interaction - start with conceptual hints or questions."
        # elif message_count == 1:
        #     ai_context += "GUIDANCE: Second hint - MUST be more specific. Name the exact data structure (like 'use a set') or show small code snippet."
        # elif message_count == 2:
        #     ai_context += "GUIDANCE: Third hint - MUST provide concrete examples. Show actual code like 'seen = set()' or 'if num in seen:'."
        # elif message_count >= 3:
        #     ai_context += "GUIDANCE: Multiple hints given - MUST provide actual working code steps. User clearly needs concrete help."
        
        # # Important note about subtasks
        # ai_context += "\n\nIMPORTANT: This guidance level is for the CURRENT SUBTASK. If the user has moved to a different subtask or problem area, start the progression fresh (treat as first interaction for that new subtask)."
        
        return ai_context

    def _track_ai_message(self, context: ConversationContext, message: str):
        """Track AI message for progressive hints"""
        print(f"🤖 TRACKING AI MESSAGE: {message[:50]}...")
        print(f"   Before tracking: {len(context.ai_message_history)} messages")
        
        # Add message to history (keep last 10 messages)
        context.ai_message_history.append(message)
        if len(context.ai_message_history) > 10:
            context.ai_message_history = context.ai_message_history[-10:]
        
        print(f"   After tracking: {len(context.ai_message_history)} messages")

    def _reset_ai_message_history(self, context: ConversationContext):
        """Reset AI message history when users make progress"""
        if context.ai_message_history:
            print(f"🔄 RESETTING AI MESSAGE HISTORY: Had {len(context.ai_message_history)} messages")
            for i, msg in enumerate(context.ai_message_history):
                print(f"   Clearing {i+1}. {msg[:50]}...")
            context.ai_message_history = []
            print(f"🔄 Reset complete. New count: {len(context.ai_message_history)}")
        else:
            print(f"🔄 Reset called but history was already empty")

    def _detect_user_progress(self, context: ConversationContext) -> bool:
        """Detect if users have made progress (to reset message history)"""
        # Check for positive indicators of progress:
        
        # 1. Successful code execution recently
        if (context.last_execution_time and 
            context.last_execution_time > datetime.now() - timedelta(minutes=2) and
            context.last_execution_success):
            return True
        
        # 2. New code added recently
        recent_messages = context.messages[-3:] if len(context.messages) >= 3 else context.messages
        for msg in recent_messages:
            # Look for keywords indicating progress
            progress_keywords = ['works', 'working', 'fixed', 'got it', 'solved', 'success', 'good', 'nice']
            if any(keyword in msg.content.lower() for keyword in progress_keywords):
                return True
        
        # 3. No AI intervention needed for a while (users working independently)
        if (context.last_ai_response and 
            datetime.now() - context.last_ai_response > timedelta(minutes=5)):
            return True
            
        return False

    def _handle_direct_ai_mention(self, room_id: str):
        """Handle direct AI mention - respond immediately bypassing ALL restrictions"""
        context = self.conversation_history.get(room_id)
        if not context:
            return
            
        if not self.client:
            print("🚫 AI cannot respond to direct mention: No LLM client available")
            return
            
        print(f"🚀 BYPASSING ALL RESTRICTIONS for direct AI mention in room {room_id}")
        
        # Force AI decision for direct mention (no restrictions)
        should_respond, message = self._centralized_ai_decision(room_id)
        
        if should_respond and message:
            # Update AI response timestamp (but no cooldown enforced for direct mentions)
            context.last_ai_response = datetime.now()
            
            # Send immediate AI response using proper chat message format
            self.send_ai_message(room_id, message)
            
            print(f"✅ AI responded IMMEDIATELY to direct mention in room {room_id}: {message[:50]}...")
        else:
            # Even if LLM says no, we should respond to direct mentions with a helpful message
            fallback_message = "I'm here to help! What specific question do you have about your code or programming problem?"
            context.last_ai_response = datetime.now()
            self.send_ai_message(room_id, fallback_message)
            print(f"✅ AI responded with fallback to direct mention in room {room_id}")

    def add_message_to_context(self, message_data: Dict[str, Any]):
        """Add a new message to the conversation context with direct AI mention detection"""
        room_id = message_data.get('room')
        if not room_id:
            return
            
        # Include ALL messages (user and AI) for reflection context
        message = Message(
            id=message_data.get('id', ''),
            content=message_data.get('content', ''),
            username=message_data.get('username', 'Unknown'),
            userId=message_data.get('userId', ''),
            timestamp=message_data.get('timestamp', ''),
            room=room_id,
            isAutoGenerated=message_data.get('isAutoGenerated', False)
        )
        
        if room_id not in self.conversation_history:
            self.conversation_history[room_id] = ConversationContext(
                messages=[],
                room_id=room_id
            )
            
        context = self.conversation_history[room_id]
        context.messages.append(message)
        
        # Track AI messages for progressive hints
        if message.userId == 'ai_agent_bob':  # This is an AI message
            self._track_ai_message(context, message.content)
        
        # Update last message time for 5-second idle timer
        context.last_message_time = datetime.now()
        
        # Check for user progress and reset AI message history if needed
        if message.userId != 'ai_agent_bob':  # Only for user messages
            if self._detect_user_progress(context):
                self._reset_ai_message_history(context)
        
        # Cancel any pending intervention since user is active
        self.intervention_service.cancel_intervention(room_id, "new message received")

        print(f"💬 New message added to context in room {room_id}: {message.content[:50]}...")
        
        # Check for direct AI mention (@AI keyword) - PRIORITY RESPONSE
        if self._is_direct_ai_mention(message.content):
            print(f"🎯 DIRECT AI MENTION detected in room {room_id}: {message.content[:50]}...")
            # Respond immediately without waiting for 5-second timer
            self._handle_direct_ai_mention(room_id)
            # DO NOT start timer for direct mentions - return early
            if len(context.messages) > 10:  # max_context_messages
                context.messages = context.messages[-10:]
            return
        
        # Trigger 30-second progress check (only if not already running)
        # Only for user messages (not AI messages)
        if message.userId != 'ai_agent_bob':
            print("📊 Triggering 30-second progress check for new message...", message)
            self.intervention_service.trigger_progress_check(room_id)
        
        # Keep only recent messages
        if len(context.messages) > 10:  # max_context_messages
            context.messages = context.messages[-10:]

    def update_code_context(self, room_id: str, code: str, language: str = "python", user_id: str = None):
        """Update the current code context for a room"""
        if room_id not in self.conversation_history:
            self.conversation_history[room_id] = ConversationContext(
                messages=[],
                room_id=room_id
            )
            
        context = self.conversation_history[room_id]
        context.code_context = code
        context.programming_language = language
        
        # Cancel pending interventions - target specific user's personal room if user_id provided
        if user_id:
            # Cancel timer for the specific user's personal room (if they're in individual mode)
            personal_room = f"{room_id}_personal_{user_id}"
            self.intervention_service.cancel_intervention(personal_room, "code update received")
            print(f"🖥️ Code updated by user {user_id} - cancelled timer for personal room: {personal_room}")
            
            # Also cancel for the main room (for shared mode compatibility)
            self.intervention_service.cancel_intervention(room_id, "code update received")
            print(f"🖥️ Code updated in room {room_id} - cancelled pending timer")
        else:
            # Fallback to original behavior if no user_id provided
            self.intervention_service.cancel_intervention(room_id, "code update received")
            print(f"🖥️ Code updated in room {room_id} - cancelled pending timer")
        
        # Check for planning intervention (only once per session)
        if not context.planning_check_done:
            print(f"🔍 Checking for planning intervention in room {room_id}")
            self._check_planning_intervention(room_id)

    def update_execution_results(self, room_id: str, code: str, output: str, error: str, success: bool):
        """Update execution results and potentially reset intervention level on success"""
        if room_id not in self.conversation_history:
            return
            
        context = self.conversation_history[room_id]
        context.last_execution_code = code
        context.last_execution_output = output
        context.last_execution_error = error
        context.last_execution_success = success
        context.last_execution_time = datetime.now()
        
        # If execution was successful, reset AI message history
        if success and not error:
            self._reset_ai_message_history(context)
            print(f"🎉 Successful execution in room {room_id} - reset AI message history")

    def update_problem_context(self, room_id: str, problem_title: str, problem_description: str):
        """Update the current problem description for a room"""
        if room_id not in self.conversation_history:
            self.conversation_history[room_id] = ConversationContext(
                messages=[],
                room_id=room_id
            )
            
        context = self.conversation_history[room_id]
        context.problem_title = problem_title
        context.problem_description = problem_description

    def should_respond(self, room_id: str) -> bool:
        """Simple decision making for AI intervention after 5-second idle"""
        return self.intervention_service.should_respond(room_id, self.conversation_history)

    def generate_response(self, room_id: str) -> Optional[str]:
        """Generate AI response using centralized decision"""
        if not self.client:
            print("⚠️  Cannot generate AI response: OpenAI client not initialized")
            return None
            
        if room_id not in self.conversation_history:
            return None
            
        context = self.conversation_history[room_id]
        
        # Check if we have a pre-generated intervention message from centralized decision
        if hasattr(context, 'pending_intervention_message') and context.pending_intervention_message:
            intervention_message = context.pending_intervention_message
            
            print(f"✅ USING CENTRALIZED INTERVENTION: {len(intervention_message.split())} words")
            print(f"   Preview: {intervention_message[:100]}{'...' if len(intervention_message) > 100 else ''}")
            
            # Update tracking
            context.last_ai_response = datetime.now()
            
            # Clear the pending message
            context.pending_intervention_message = None
            
            return intervention_message
        else:
            print("⚠️  No centralized intervention message found")
            return None

    def send_ai_message(self, room_id: str, content: str, is_reflection: bool = False):
        """Send an AI message to the chat room"""
        # Track AI message for progressive hints (only for non-reflection messages)
        if not is_reflection and room_id in self.conversation_history:
            context = self.conversation_history[room_id]
            self._track_ai_message(context, content)
        
        message = self.audio_service.send_ai_message(
            room_id, content, is_reflection, False, self.conversation_history
        )
        
        # Always add AI message to conversation context, even if audio service returns None
        # (audio service may return None for async operations but still sends the message)
        if message:
            # Use the message object returned by audio service
            self.add_message_to_context(message)
        else:
            # Create a message object manually to ensure it's added to context
            manual_message = {
                'id': f"ai_{int(time.time() * 1000)}",
                'content': content,
                'username': self.agent_name,  # Use consistent agent name
                'userId': self.agent_id,
                'timestamp': datetime.now().isoformat(),
                'room': room_id,
                'isAutoGenerated': True,
                'isReflection': is_reflection
            }
            self.add_message_to_context(manual_message)
            print(f"🤖 Manually added AI message to context: {content[:50]}...")


    def process_message_sync(self, message_data: Dict[str, Any]):
        """Process a new message and potentially respond"""
        try:
            # Add message to context first
            self.add_message_to_context(message_data)
            
            room_id = message_data.get('room')
            if not room_id or room_id not in self.conversation_history:
                return
            
            # Check if this is a reflection trigger (system message starting reflection)
            if message_data.get('isReflectionTrigger', False):
                print(f"🎓 Reflection trigger detected: Starting reflection response for room {room_id}")
                
                # Get reflection service dynamically
                if not self.reflection_service:
                    self.reflection_service = get_reflection_service()
                
                if self.reflection_service:
                    self.reflection_service.send_reflection_opening(room_id, self.send_ai_message)
                else:
                    print("❌ Error: Reflection service not available for opening")
                return
            
            # Check if this is reflection mode
            is_reflection = message_data.get('isReflectionMode', False)
            
            if is_reflection:
                print(f"🎓 Reflection mode: Starting 5s timer for room {room_id}")
                # Always respond after 5s in reflection mode
                self.intervention_service.schedule_reflection_response(room_id)
                return
            
            # Regular AI logic
            # Check if this is a direct AI mention BEFORE adding to context
            is_direct_mention = self._is_direct_ai_mention(message_data.get('content', ''))
            
            # Only start timer for non-direct mentions
            if not is_direct_mention:
                # Start new 5-second idle timer
                self.intervention_service.schedule_idle_intervention(room_id)
                
        except Exception as e:
            print(f"Error processing message in AI agent: {e}")

    def handle_code_update(self, room_id: str, code: str, language: str = "python", user_id: str = None):
        """Handle code updates from the editor"""
        self.update_code_context(room_id, code, language, user_id)
        
    def handle_problem_update(self, room_id: str, problem_title: str, problem_description: str):
        """Handle problem description updates"""
        self.update_problem_context(room_id, problem_title, problem_description)

    def release_generation_lock(self, room_id: str, message_id: str = None):
        """Release AI generation lock when audio playback is complete"""
        if room_id in self.conversation_history:
            print(f"🔓 Audio playback complete for room {room_id} (message: {message_id})")
        else:
            print(f"⚠️ AI RESPONSE LOCK: No context found for room {room_id}")

    def join_room(self, room_id: str):
        """AI agent joins a room (but doesn't send greeting until session starts)"""
        # Reset AI message history for fresh room join (regardless of OpenAI client)
        if room_id not in self.conversation_history:
            # Initialize context if it doesn't exist
            self.conversation_history[room_id] = ConversationContext(
                messages=[],
                room_id=room_id
            )
        context = self.conversation_history[room_id]
        self._reset_ai_message_history(context)
        print(f"🔄 Reset AI message history for fresh room join: {room_id}")
        
        # Only proceed with OpenAI functionality if client is available
        if not self.client:
            print(f"⚠️  Bob cannot join room {room_id}: OpenAI client not initialized")
            return
            
        print(f"🤖 Bob joined room {room_id} and is ready for session start")

    def send_session_start_greeting(self, room_id: str):
        """Send greeting when session is actually started"""
        if not self.client:
            print(f"⚠️  Bob cannot send greeting for room {room_id}: OpenAI client not initialized")
            return
            
        # Reset AI message history for fresh session start
        if room_id not in self.conversation_history:
            # Initialize context if it doesn't exist
            self.conversation_history[room_id] = ConversationContext(
                messages=[],
                room_id=room_id
            )
        context = self.conversation_history[room_id]
        self._reset_ai_message_history(context)
        print(f"🔄 Reset AI message history for new session in room {room_id}")
            
        # Send a greeting message when session starts
        greeting_messages = [
            "Welcome! I'm here to support your pair programming session. I'll offer technical guidance and help maintain productive collaboration.",
        ]
        
        greeting = random.choice(greeting_messages)
        
        # Send greeting after a short delay (non-blocking)
        def send_greeting():
            time.sleep(1)  # Wait 1 second before greeting
            # Use send_ai_message to ensure the greeting is added to context
            self.send_ai_message(room_id, greeting, is_reflection=False)
            
        # Start greeting in a separate thread to avoid blocking
        threading.Thread(target=send_greeting, daemon=True).start()

    def set_voice_config(self, voice: str = None, model: str = None, speed: float = None):
        """Update voice configuration for TTS"""
        self.audio_service.set_voice_config(voice, model, speed)

    def analyze_code_block(self, code: str, language: str, context: Dict[str, Any], 
                          problem_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze a code block for potential issues and provide suggestions"""
        return self.code_analysis_service.analyze_code_block(code, language, context, problem_context)

    def start_panel_analysis(self, room_id: str, code: str, result: dict):
        """Start non-blocking AI analysis for execution panel"""
        # Update execution results and reset intervention level if successful
        output = result.get('output', '')
        error = result.get('error', '')
        success = result.get('success', True)
        self.update_execution_results(room_id, code, output, error, success)
        
        # Start the panel analysis
        self.code_analysis_service.start_panel_analysis(room_id, code, result, self.conversation_history)


    def _check_planning_intervention(self, room_id: str):
        """Check if planning intervention is needed when code is first written"""
        try:
            if not self.client:
                print("⚠️ Cannot check planning: No LLM client available")
                return
            
            context = self.conversation_history.get(room_id)
            if not context:
                return
            
            # Check if there are any user chat messages (indicating session activity)
            if len(context.messages) == 0:
                print("🔍 Planning intervention skipped: No user chat messages yet (session not started)")
                return
            
            # Mark as done to prevent multiple checks
            context.planning_check_done = True
            
            # Build conversation history for LLM
            conversation = ""
            for msg in context.messages:
                conversation += f"{msg.username}: {msg.content}\n"
            
            # Single LLM call to decide if planning intervention is needed
            prompt = f"""You are Bob, an AI pair programming assistant. A user just started writing code.

Problem Context: {context.problem_description or context.problem_title or "General coding task"}

Conversation so far:
{conversation}

Current code being written:
```{context.programming_language}
{context.code_context[:200]}
```

TASK: Analyze if the users have discussed a proper plan before coding.

Good planning indicators:
- Discussed approach, algorithm, or strategy
- Talked about steps or breakdown
- Mentioned data structures or methods to use
- Asked questions about the problem

Respond with ONE of these formats:
- If they have a plan: "NO_INTERVENTION"
- If no planning discussion: "ASK_PLAN|What's your approach? Let's discuss the plan before diving into code!"
- If some discussion but needs more detail: "DETAILED_PLAN|I see you're thinking about this. Can you break down your approach step by step?"

Your response:"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful pair programming assistant focused on encouraging good planning practices."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.3
            )
            
            llm_response = response.choices[0].message.content.strip()
            print(f"🧠 Planning LLM response: {llm_response}")
            
            # Parse LLM response and send intervention if needed
            if llm_response.startswith("ASK_PLAN|") or llm_response.startswith("DETAILED_PLAN|"):
                parts = llm_response.split("|", 1)
                if len(parts) >= 2:
                    intervention_message = parts[1]
                    print(f"📋 Sending planning intervention: {intervention_message}")
                    self.send_ai_message(room_id, intervention_message)
            else:
                print(f"📋 No planning intervention needed for room {room_id}")
                
        except Exception as e:
            print(f"❌ Error in planning intervention check: {e}")
            # Mark as done even on error to prevent retries
            if room_id in self.conversation_history:
                self.conversation_history[room_id].planning_check_done = True

    def reset_room_state(self, room_id: str):
        """Reset all AI agent state for a specific room"""
        try:
            print(f"🔄 Resetting AI agent state for room {room_id}")
            
            # Cancel any pending interventions (includes progress timers)
            self.intervention_service.cleanup_room(room_id)
            
            # Remove conversation history
            if room_id in self.conversation_history:
                del self.conversation_history[room_id]
                print(f"🗑️ Cleared conversation history for room {room_id}")
            
            # Clear code analysis tracking
            self.code_analysis_service.reset_execution_tracking(room_id)
            
            # Clear individual AI conversations for all users in this room
            from .individual_ai_service import get_individual_ai_service
            individual_ai = get_individual_ai_service()
            if individual_ai:
                individual_ai.clear_room_conversations(room_id)
            
            print(f"✅ Successfully reset AI agent state for room {room_id}")
            
        except Exception as e:
            print(f"❌ Error resetting AI agent state for room {room_id}: {e}")

    def get_room_state_summary(self, room_id: str) -> Dict[str, Any]:
        """Get a summary of current room state for debugging"""
        try:
            context = self.conversation_history.get(room_id)
            
            summary = {
                "room_id": room_id,
                "has_context": context is not None,
                "message_count": len(context.messages) if context else 0,
                "planning_check_done": context.planning_check_done if context else False,
                "has_code_context": bool(context.code_context) if context else False,
                "has_problem_context": bool(context.problem_description or context.problem_title) if context else False,
                "last_ai_response": context.last_ai_response.isoformat() if context and context.last_ai_response else None,
                "has_pending_timer": self.intervention_service.has_pending_timer(room_id),
                # AI message tracking
                "ai_message_history_count": len(context.ai_message_history) if context else 0,
            }
            
            return summary
            
        except Exception as e:
            print(f"❌ Error getting room state summary: {e}")
            return {"error": str(e)}

    # Progress tracking methods
    # Progress tracking methods
    def cancel_progress_check(self, room_id: str, reason: str):
        """Cancel 30-second progress tracking for a room"""
        self.intervention_service.cancel_progress_check(room_id, reason)
    
    def has_progress_timer(self, room_id: str) -> bool:
        """Check if room has a pending progress timer"""
        return self.intervention_service.has_progress_timer(room_id)
    
    def get_active_progress_rooms(self):
        """Get list of rooms with active progress timers"""
        return self.intervention_service.get_active_progress_rooms()

    # Public methods for accessing intervention service functionality
    def cancel_pending_intervention(self, room_id: str, reason: str):
        """Public method to cancel pending interventions"""
        self.intervention_service.cancel_intervention(room_id, reason)

    def has_pending_timer(self, room_id: str) -> bool:
        """Check if room has a pending timer"""
        return self.intervention_service.has_pending_timer(room_id)

    def get_pending_timer_rooms(self) -> List[str]:
        """Get list of rooms with pending timers"""
        return list(self.intervention_service.pending_timers.keys())

    # Backward compatibility properties
    @property
    def pending_timers(self):
        """Backward compatibility access to pending timers"""
        return self.intervention_service.pending_timers

    def _cancel_pending_intervention(self, room_id: str, reason: str):
        """Backward compatibility method"""
        self.intervention_service.cancel_intervention(room_id, reason)


# Global AI agent instance
ai_agent = None

def init_ai_agent(socketio_instance):
    """Initialize the AI agent"""
    global ai_agent
    ai_agent = AIAgent(socketio_instance)
    return ai_agent

def get_ai_agent():
    """Get the global AI agent instance"""
    return ai_agent
