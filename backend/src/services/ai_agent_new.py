"""
AI Agent Service - A proactive AI teammate for pair programming
Uses GPT-4o-mini to analyze conversations and provide helpful insights

This module provides a simplified interface to the modular AI agent system.
The original large file has been decomposed into specialized service modules:
- ai_agent_core.py: Main AIAgent class with core functionality
- ai_models.py: Data classes and models
- ai_audio.py: Audio/TTS streaming functionality
- ai_intervention.py: Timer management and intervention logic
- ai_code_analysis.py: Code analysis and execution validation
- ai_reflection.py: Reflection mode functionality
"""

# Import the new modular AI agent
from .ai_agent_core import AIAgent as CoreAIAgent, init_ai_agent as core_init_ai_agent, get_ai_agent as core_get_ai_agent
from .ai_models import Message, ConversationContext

# Re-export the main class and functions for backward compatibility
class AIAgent(CoreAIAgent):
    """Backward compatible AIAgent class"""
    pass

# Global AI agent instance for backward compatibility
ai_agent = None

def init_ai_agent(socketio_instance):
    """Initialize the AI agent and set global reference"""
    agent = core_init_ai_agent(socketio_instance)
    global ai_agent
    ai_agent = agent
    return agent

def get_ai_agent():
    """Get the global AI agent instance"""
    return core_get_ai_agent()
