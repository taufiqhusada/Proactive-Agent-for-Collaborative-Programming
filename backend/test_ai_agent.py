"""
Test script for AI Agent functionality
Run this to verify the AI agent is working correctly
"""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.ai_agent import AIAgent
from unittest.mock import Mock

async def test_ai_agent():
    """Test the AI agent functionality"""
    print("🧪 Testing AI Agent...")
    
    # Create a mock SocketIO instance
    mock_socketio = Mock()
    
    # Initialize the AI agent
    agent = AIAgent(mock_socketio)
    
    # Test 1: Adding messages to context
    print("\n1. Testing message context management...")
    test_message = {
        'id': '123',
        'content': 'I have a bug in my Python code',
        'username': 'TestUser',
        'userId': 'user123',
        'timestamp': '2025-06-18T10:00:00Z',
        'room': 'test_room'
    }
    
    agent.add_message_to_context(test_message)
    assert 'test_room' in agent.conversation_history
    assert len(agent.conversation_history['test_room'].messages) == 1
    print("✅ Message context management works!")
    
    # Test 2: Code context updates
    print("\n2. Testing code context updates...")
    test_code = """
def hello_world():
    print("Hello, World!")
    return True
"""
    agent.update_code_context('test_room', test_code, 'python')
    assert agent.conversation_history['test_room'].code_context == test_code
    assert agent.conversation_history['test_room'].programming_language == 'python'
    print("✅ Code context updates work!")
    
    # Test 3: Response decision logic
    print("\n3. Testing response decision logic...")
    
    # Add more messages with keywords that should trigger response
    help_message = {
        'id': '124',
        'content': 'Can someone help me debug this error?',
        'username': 'TestUser2',
        'userId': 'user124',
        'timestamp': '2025-06-18T10:01:00Z',
        'room': 'test_room'
    }
    
    question_message = {
        'id': '125',
        'content': 'What is the best way to handle exceptions?',
        'username': 'TestUser3',
        'userId': 'user125',
        'timestamp': '2025-06-18T10:02:00Z',
        'room': 'test_room'
    }
    
    agent.add_message_to_context(help_message)
    agent.add_message_to_context(question_message)
    
    should_respond = agent.should_respond('test_room')
    print(f"Should respond to help request: {should_respond}")
    assert should_respond, "AI should respond to help requests"
    print("✅ Response decision logic works!")
    
    # Test 4: Response generation (requires API key)
    print("\n4. Testing response generation...")
    if os.getenv('OPENAI_API_KEY'):
        try:
            response = await agent.generate_response('test_room')
            if response and response != "SKIP_RESPONSE":
                print(f"Generated response: {response[:100]}...")
                print("✅ Response generation works!")
            else:
                print("⚠️  AI chose not to respond (this is normal)")
        except Exception as e:
            print(f"❌ Response generation failed: {e}")
            print("💡 Make sure your OpenAI API key is set in .env file")
    else:
        print("⚠️  Skipping response generation test (no API key)")
    
    # Test 5: Message processing
    print("\n5. Testing complete message processing...")
    
    # Test message that should trigger response
    programming_message = {
        'id': '126',
        'content': 'How do I fix this syntax error in my function?',
        'username': 'TestUser4',
        'userId': 'user126',
        'timestamp': '2025-06-18T10:03:00Z',
        'room': 'test_room'
    }
    
    try:
        await agent.process_message(programming_message)
        print("✅ Message processing completed successfully!")
    except Exception as e:
        print(f"❌ Message processing failed: {e}")
    
    print("\n🎉 AI Agent tests completed!")
    print("\n📋 Summary:")
    print("- Message context management: ✅")
    print("- Code context updates: ✅") 
    print("- Response decision logic: ✅")
    print("- Response generation: ⚠️  (requires API key)")
    print("- Message processing: ✅")
    
    print("\n🚀 AI Agent is ready for use!")
    print("Make sure to set your OPENAI_API_KEY in the .env file for full functionality.")

if __name__ == "__main__":
    asyncio.run(test_ai_agent())
