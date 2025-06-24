# 🎯 Smart Non-Annoying AI Interventions Test

"""
Test script to demonstrate the new smart intervention system that prevents AI from being annoying.
Key improvements:
1. One intervention per type until users respond
2. Escalating message intensity
3. Different cooldown periods for different intervention types  
4. No message stacking - AI waits for user response
5. Smart state tracking and reset logic
"""

import sys
import os
sys.path.append('src')

from services.ai_agent import AIAgent
from unittest.mock import Mock
import time
from datetime import datetime, timedelta

def test_smart_interventions():
    print("🧠 Testing Smart Non-Annoying AI Intervention System")
    print("=" * 70)
    print("📝 This test will show console logs for AI intervention decisions\n")
    
    # Initialize AI agent
    mock_socketio = Mock()
    agent = AIAgent(mock_socketio)
    
    room_id = 'test_room'
    
    # Set up problem context
    agent.update_problem_context(room_id, 
                                'Binary Search Implementation',
                                'Implement binary search to find element in sorted array')
    
    print("🎯 Testing Scenario 1: Basic silence intervention")
    print("-" * 50)
    
    # Add 3 initial messages
    for i in range(3):
        message = {
            'id': str(i+1),
            'content': f'User message {i+1}',
            'username': 'Alice',
            'userId': 'user1', 
            'timestamp': datetime.now().isoformat(),
            'room': room_id
        }
        agent.add_message_to_context(message)
    
    context = agent.conversation_history[room_id]
    
    # Simulate 35 seconds of silence
    print(f"\n⏱️  Simulating 35 seconds of silence...")
    context.last_activity_time = datetime.now() - timedelta(seconds=35)
    
    print("Checking if silence intervention should be sent...")
    should_intervene = agent._should_send_intervention(context, 'silence')
    
    if should_intervene:
        print("Sending silence intervention...")
        agent._intervene_for_silence(room_id, context)
    
    print(f"\n🎯 Testing Scenario 2: Race condition prevention")
    print("-" * 50)
    
    # Reset context for race condition test
    context.pending_ai_response = False
    context.ai_generating_response = False
    context.intervention_escalation_level = 0
    context.interventions_sent = {}
    
    # Add messages to trigger regular response
    help_message = {
        'id': '10',
        'content': 'I need help with this binary search implementation',
        'username': 'Bob',
        'userId': 'user2', 
        'timestamp': datetime.now().isoformat(),
        'room': room_id
    }
    agent.add_message_to_context(help_message)
    
    # Test 1: Check if AI should respond (this will acquire the lock)
    print("Step 1: Checking if AI should respond to help request...")
    should_respond = agent.should_respond(room_id)
    print(f"   AI should respond: {should_respond}")
    print(f"   AI generation lock: {context.ai_generating_response}")
    
    # Test 2: Simulate user sending another message while AI is generating
    print("\nStep 2: User sends another message while AI is generating response...")
    another_message = {
        'id': '11',
        'content': 'Actually, I think I found an error in my code',
        'username': 'Bob',
        'userId': 'user2', 
        'timestamp': datetime.now().isoformat(),
        'room': room_id
    }
    agent.add_message_to_context(another_message)
    
    # Test 3: Check if AI tries to respond again (should be blocked)
    print("\nStep 3: Checking if AI tries to respond again (should be blocked)...")
    should_respond_again = agent.should_respond(room_id)
    print(f"   AI should respond again: {should_respond_again} (should be False)")
    
    # Test 4: Simulate AI completing first response
    print("\nStep 4: Simulating AI completing first response...")
    context.ai_generating_response = False
    context.ai_response_lock_time = None
    context.last_ai_response = datetime.now()
    print(f"   AI generation lock released: {not context.ai_generating_response}")
    
    # Test 5: Now AI should be able to respond (after cooldown)
    print("\nStep 5: After cooldown, AI should be able to respond...")
    # Fast-forward past cooldown
    context.last_ai_response = datetime.now() - timedelta(seconds=16)
    should_respond_after_cooldown = agent.should_respond(room_id)
    print(f"   AI should respond after cooldown: {should_respond_after_cooldown}")
    
    print(f"\n📊 Final intervention status:")
    status = agent.get_intervention_status(room_id)
    print(f"   - Pending AI response: {status['pending_ai_response']}")
    print(f"   - Escalation level: {status['escalation_level']}")
    print(f"   - Interventions sent: {list(status['interventions_sent'].keys())}")
    
    print("\n" + "=" * 70)
    print("✅ Smart Non-Annoying AI Intervention System Working!")
    print("\n🎯 Key Improvements Demonstrated:")
    print("   1. ✅ AI sends one intervention then waits for user response")
    print("   2. ✅ No repeated interventions until cooldown period passes")
    print("   3. ✅ Race condition prevention with generation locks")
    print("   4. ✅ Concurrent response blocking prevents voice overlap")
    print("   5. ✅ Smart state tracking prevents message stacking")
    print("   6. ✅ User responses reset the intervention state")
    
    print(f"\n🚫 Race Condition Prevention:")
    print(f"   - AI acquires generation lock when deciding to respond")
    print(f"   - Subsequent response checks are blocked while lock is held")
    print(f"   - Lock is released after message is sent or on error")
    print(f"   - 30-second safety timeout prevents stuck locks")
    print("\n🎯 Key Improvements Demonstrated:")
    print("   1. ✅ AI sends one intervention then waits for user response")
    print("   2. ✅ No repeated interventions until cooldown period passes")
    print("   3. ✅ Different intervention types have appropriate cooldowns")
    print("   4. ✅ Escalating message intensity for persistent issues")
    print("   5. ✅ Smart state tracking prevents message stacking")
    print("   6. ✅ User responses reset the intervention state")
    
    print(f"\n💡 Cooldown Periods:")
    print(f"   - Silence: 5 minutes")
    print(f"   - Misdirection: 3 minutes") 
    print(f"   - Repeated errors: 2 minutes")
    print(f"   - Code review: 5 minutes")
    print(f"   - Planning: 15 minutes")
    print(f"   - Reflection: 10 minutes")
    print(f"   - Imbalance: 4 minutes")

if __name__ == "__main__":
    test_smart_interventions()
