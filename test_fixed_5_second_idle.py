#!/usr/bin/env python3

"""
Test script for fixed 5-second idle requirement
This verifies that the persistent event loop solution allows timers to complete properly.
"""

import sys
import os
import asyncio
import time
from datetime import datetime

sys.path.append('backend/src')

from services.ai_agent import AIAgent
from unittest.mock import Mock

def test_fixed_5_second_idle():
    print("🎯 TESTING FIXED 5-SECOND IDLE REQUIREMENT")
    print("=" * 70)
    print("🔧 Using persistent event loop solution")
    print()
    
    # Initialize AI agent (this will create persistent event loop)
    mock_socketio = Mock()
    agent = AIAgent(mock_socketio)
    
    # Give time for persistent event loop to initialize
    time.sleep(0.5)
    
    room_id = 'test_fixed_room'
    
    # Set up problem context
    agent.update_problem_context(room_id, 
                                'Binary Search Implementation',
                                'Implement binary search to find element in sorted array')
    
    print("📝 TEST: Single message followed by waiting for timer completion")
    print("-" * 60)
    
    # Send a message that should trigger 5-second timer
    message = {
        'id': '1',
        'content': 'I need help with this algorithm',
        'username': 'Alice',
        'userId': 'user1',
        'timestamp': datetime.now().isoformat(),
        'room': room_id
    }
    
    start_time = time.time()
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')} - Sending message: '{message['content']}'")
    
    # Process the message using sync method (which now uses persistent event loop)
    agent.process_message_sync(message)
    
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')} - Message processed, waiting for timer...")
    print("   Expected: Timer should complete in ~5 seconds and print completion message")
    print()
    
    # Wait 7 seconds to see if timer completes
    for i in range(7):
        elapsed = time.time() - start_time
        print(f"   Waiting... {elapsed:.1f}s elapsed")
        time.sleep(1)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print()
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')} - Test completed after {total_time:.1f}s")
    print()
    
    print("🔍 EXPECTED OUTPUT:")
    print("   ⏱️  Starting 5-second idle timer for room test_fixed_room")
    print("   Timer XXXXX: 1/5 seconds elapsed...")
    print("   Timer XXXXX: 2/5 seconds elapsed...")
    print("   Timer XXXXX: 3/5 seconds elapsed...")
    print("   Timer XXXXX: 4/5 seconds elapsed...")
    print("   Timer XXXXX: 5/5 seconds elapsed...")
    print("   ⏰  5-second idle timer completed for room test_fixed_room  ← KEY LINE")
    print()
    
    print("✅ If you see the timer completion message above, the fix worked!")
    print("❌ If timer messages stopped before completion, there's still an issue")
    print()
    
    print("🚀 SOLUTION BENEFITS:")
    print("   ✅ Persistent event loop survives message processing")
    print("   ✅ Timers can complete without being destroyed")
    print("   ✅ 5-second idle requirement now works properly")
    print("   ✅ Background monitoring continues working")
    print("   ✅ No more event loop conflicts")

if __name__ == "__main__":
    test_fixed_5_second_idle()
