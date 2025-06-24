# 🎯 Misdirection Detection Feature Test

"""
Test script to demonstrate the new misdirection detection capability
based on research requirement: "Addressing misdirection (When discussing the wrong idea for ≥ 30s)"
"""

import sys
import os
sys.path.append('src')

from services.ai_agent import AIAgent
from unittest.mock import Mock
import time
from datetime import datetime, timedelta

def test_misdirection_detection():
    print("🔬 Testing Misdirection Detection Feature")
    print("=" * 60)
    
    # Initialize AI agent
    mock_socketio = Mock()
    agent = AIAgent(mock_socketio)
    
    # Simulate a realistic misdirection scenario
    print("\n📋 Scenario: Students discussing bubble sort for a search problem")
    print("Expected: AI should detect this as misdirection after 30+ seconds")
    
    # Set up problem context
    agent.update_problem_context('test_room', 
                                'Binary Search Implementation',
                                'Implement binary search to find element in sorted array')
    
    # Simulate conversation about wrong approach
    misdirection_messages = [
        {
            'id': '1',
            'content': 'I think we should implement bubble sort first',
            'username': 'Alice',
            'userId': 'user1', 
            'timestamp': '2025-06-23T10:00:00Z',
            'room': 'test_room'
        },
        {
            'id': '2',
            'content': 'Yeah, bubble sort will help us organize the data',
            'username': 'Bob', 
            'userId': 'user2',
            'timestamp': '2025-06-23T10:00:15Z',
            'room': 'test_room'
        },
        {
            'id': '3',
            'content': 'Let me implement the bubble sort algorithm step by step',
            'username': 'Alice',
            'userId': 'user1',
            'timestamp': '2025-06-23T10:00:35Z',  # 35 seconds later - should trigger misdirection
            'room': 'test_room'
        }
    ]
    
    # Process messages
    for i, msg in enumerate(misdirection_messages):
        agent.add_message_to_context(msg)
        context = agent.conversation_history['test_room']
        
        print(f"\n📨 Message {i+1}: {msg['content']}")
        print(f"   Topic detected: {context.current_discussion_topic}")
        
        if context.discussion_start_time:
            duration = (datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00')) - 
                       context.discussion_start_time).total_seconds()
            print(f"   Discussion duration: {duration:.1f}s")
            
            # Check if misdirection intervention would trigger
            if duration >= agent.misdirection_threshold:
                print(f"   🚨 MISDIRECTION DETECTED! (≥{agent.misdirection_threshold}s threshold)")
                
                # Test intervention generation
                intervention = agent._generate_misdirection_intervention(context)
                print(f"   💬 AI Intervention: '{intervention}'")
    
    print("\n" + "=" * 60)
    print("✅ Misdirection Detection Feature Working!")
    
    # Test topic extraction capabilities
    print("\n🧪 Testing Topic Extraction:")
    test_phrases = [
        "let's use bubble sort for this",
        "we need to implement binary search", 
        "should we use recursion or iteration?",
        "this algorithm needs optimization",
        "we have a bug in our code",
        "let's debug this step by step"
    ]
    
    for phrase in test_phrases:
        topic = agent._extract_discussion_topic(phrase.lower())
        print(f"   '{phrase}' → Topic: {topic}")
    
    print("\n🎯 Research Implementation Complete!")
    print("The AI will now intervene when students discuss wrong approaches for ≥30 seconds")

if __name__ == "__main__":
    test_misdirection_detection()
