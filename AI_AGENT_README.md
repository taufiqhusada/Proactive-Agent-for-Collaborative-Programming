# AI Agent Integration for Pair Programming

This document describes the implementation of an optimized AI agent that acts as a third teammate in the pair programming environment.

## Overview

The AI agent, named "CodeBot", uses OpenAI's GPT-4o-mini model for intelligent assistance and can:
- Listen passively to ongoing conversations between programmers
- Proactively join discussions when help is needed or questions arise
- Understand the context of code being written and current problems
- Provide intelligent suggestions and code improvements
- Answer programming questions with both text and optional high-quality voice responses
- Offer alternative approaches and debugging assistance

## Key Features

### 🎯 **Proactive Intelligence**
- **Smart Listening**: Monitors chat conversations for opportunities to help
- **Context-Aware Responses**: Always understands the current programming problem
- **Keyword Triggers**: Responds to help requests, questions, and confusion indicators
- **Non-Intrusive**: Only joins when genuinely helpful, never interrupts flow

### 🗣️ **High-Quality Voice Features**
- **OpenAI TTS Integration**: Natural-sounding voice using OpenAI's advanced text-to-speech
- **Audio Isolation**: Comprehensive feedback prevention system
- **Optional Voice**: Users can toggle voice responses on/off as needed
- **Multiple Voice Options**: Choose from different OpenAI voice models

### 💬 **Seamless Chat Integration**
- **Visual AI Indicators**: Clear 🤖 badges to identify AI messages
- **Real-time Responses**: Fast text responses (0.5-1s typical)
- **Conversation History**: All interactions visible to team members
- **Smart Formatting**: Well-structured, concise responses (70-word limit)

## Technical Implementation

### Backend Components

#### 1. AI Agent Service (`/backend/src/services/ai_agent.py`)
- **AIAgent Class**: Optimized service using OpenAI GPT-4o-mini
- **Proactive Monitoring**: Analyzes chat messages for help opportunities
- **Context Integration**: Accesses current problem description and code context
- **Performance Optimized**: Multiple optimizations for 40-50% faster responses
- **Word Limit**: Concise 70-word responses for faster processing
- **Audio Integration**: Optional high-quality OpenAI TTS for voice responses

#### 2. Flask-SocketIO Integration (`/backend/src/app.py`)
- **Chat Message Processing**: Handles incoming messages and triggers AI responses
- **Problem Context**: Provides current coding problem to AI for context-aware responses
- **Audio Generation**: Handles TTS requests for voice responses
- **Session Lifecycle Management**: Creates and manages Realtime API sessions per room

### Frontend Components

#### 1. AI Agent Status (`/frontend/src/components/AIAgentStatus.vue`)
- **Visual Indicator**: Shows that CodeBot is active and listening
- **Status Animation**: Animated dot indicating real-time activity
- **Description**: Explains the AI agent's capabilities to users

#### 2. Enhanced Chat (`/frontend/src/components/PairChat.vue`)
- **AI Message Styling**: Special styling for AI-generated messages
- **Badge System**: 🤖 emoji badge for AI messages
- **Message Classification**: Distinguishes between user, AI, and system messages

## Configuration

### Environment Variables
Create a `.env` file in the backend directory:

```bash
# Flask settings
FLASK_SECRET=your-flask-secret-key-here
JWT_SECRET=your-jwt-secret-key-here

# OpenAI API Key - Required for AI Agent
OPENAI_API_KEY=your-openai-api-key-here
```

### AI Agent Parameters
The AI agent behavior can be customized in `ai_agent.py`:

```python
self.response_cooldown = 15  # Minimum seconds between AI responses
self.min_messages_before_response = 3  # Wait for at least 3 messages
self.max_context_messages = 10  # Keep last 10 messages for context
```

## Usage

### Starting the System

1. **Backend Setup**:
   ```bash
   cd backend
   pip install -r requirements.txt
   # Add your OpenAI API key to .env file
   python src/app.py
   ```

2. **Frontend Setup**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

### Using the AI Agent

1. **Automatic Activation**: CodeBot joins automatically when users enter a room
2. **Trigger Responses**: Ask programming questions or mention keywords like:
   - "error", "bug", "problem", "help"
   - Programming terms: "function", "variable", "loop", "debug"
   - Direct questions with "?" marks
3. **Context Sharing**: The AI sees both chat messages and current code
4. **Natural Interaction**: Treat CodeBot as a helpful team member

### Example Interactions

**User**: "I'm getting a syntax error in this function"
**CodeBot**: "🤖 I can see the function you're working on. The syntax error is likely on line 5 where you're missing a closing parenthesis. Try adding ')' after the print statement."

**User**: "What's a better way to handle this loop?"
**CodeBot**: "🤖 For better performance, you could use a list comprehension instead of the for loop. This would be more Pythonic: `result = [x*2 for x in items if x > 0]`"

## AI Response Logic

The AI agent uses several criteria to determine when to respond:

### Trigger Keywords
- **Help Keywords**: error, bug, problem, stuck, help, question, debug, fix
- **Programming Keywords**: function, class, method, variable, loop, array, etc.
- **Direct Questions**: Messages containing "?" 

### Context Analysis
- **Recent Messages**: Analyzes last 3-5 messages for relevant content
- **Code Context**: Considers current code being edited
- **Conversation Flow**: Avoids interrupting natural discussion

### Response Generation
- **System Prompt**: Detailed instructions for helpful, concise responses
- **Code Context**: Includes current code in the prompt for relevant suggestions
- **Conversation History**: Uses recent messages for context-aware responses

## Customization

### Modifying AI Behavior
Edit the system prompt in `ai_agent.py`:

```python
system_prompt = f"""You are CodeBot, an AI pair programming assistant...
Your role:
1. Provide helpful programming insights and suggestions
2. Answer questions about code, debugging, or programming concepts
3. Suggest improvements or alternative approaches
4. Help resolve errors or issues
5. Be concise but helpful (keep responses under 150 words)
6. Be encouraging and collaborative
"""
```

### Adding New Trigger Keywords
Update the keyword lists in the `should_respond` method:

```python
help_keywords = [
    'error', 'bug', 'problem', 'issue', 'stuck', 'help', 'question',
    # Add your custom keywords here
]
```

### Styling AI Messages
Modify the CSS in `PairChat.vue`:

```css
.message.ai-message {
    background: linear-gradient(135deg, #10b981, #059669);
    color: white;
    border-left: 4px solid #065f46;
    box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2);
}
```

## Security Considerations

1. **API Key Protection**: Store OpenAI API key in environment variables
2. **Rate Limiting**: Built-in cooldown prevents API abuse
3. **Content Filtering**: AI responses are generated with appropriate constraints
4. **Context Limits**: Limited context window prevents excessive API usage

## Troubleshooting

### Common Issues

1. **AI Not Responding**:
   - Check OpenAI API key is set correctly
   - Verify internet connection
   - Check console for error messages

2. **Build Errors**:
   - Ensure all dependencies are installed
   - Check TypeScript compilation errors
   - Verify component imports

3. **Socket Connection Issues**:
   - Ensure backend server is running
   - Check CORS configuration
   - Verify WebSocket connections

### Debugging

Enable debug logging in the AI agent:
```python
# Add to ai_agent.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check browser console for frontend issues:
```javascript
// In browser console
console.log('Socket connected:', socket.connected)
```

## Future Enhancements

### Planned Features
- **Voice Interaction**: AI agent responding via text-to-speech
- **Code Suggestions**: Real-time code completion and suggestions
- **Learning Adaptation**: AI learning from team preferences
- **Multiple Personality Modes**: Different AI assistant personalities
- **Integration with IDEs**: Direct code editing capabilities

### Extensibility
The AI agent is designed to be easily extensible:
- Add new programming language support
- Integrate with different LLM providers
- Implement custom response templates
- Add team-specific knowledge bases

## Dependencies

### Backend
- `openai==1.6.0` - OpenAI API client
- `flask-socketio` - WebSocket support
- `python-dotenv` - Environment variable management

### Frontend
- `vue-codemirror` - Code editor component
- `socket.io-client` - WebSocket client
- `vue-router` - Navigation

## License
This AI agent implementation is part of the Human-Human-AI Pair Programming research project.
