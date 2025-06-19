# Quick Start Guide: AI Agent for Pair Programming

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 16+
- OpenAI API Key

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Create .env file with your OpenAI API key
echo "OPENAI_API_KEY=your-api-key-here" > .env
echo "FLASK_SECRET=your-secret-key" >> .env
echo "JWT_SECRET=your-jwt-secret" >> .env

# Start the backend server
python src/app.py
```

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

### 3. Using the AI Agent

1. **Access the app**: Open http://localhost:5173
2. **Login**: Use any username and password "password"
3. **Join a room**: Enter a room number
4. **Start coding**: The AI agent "CodeBot" will automatically join
5. **Get help**: Ask programming questions or mention errors/bugs

## 🤖 AI Agent Features

### What CodeBot Can Do
- **Answer Programming Questions**: Ask about syntax, best practices, algorithms
- **Debug Code Issues**: Mention errors or bugs to get help
- **Suggest Improvements**: Get recommendations for better code
- **Provide Context-Aware Help**: AI sees both chat and current code

### How to Trigger CodeBot
- Ask questions with "?" 
- Mention keywords like: error, bug, help, debug, question
- Discuss programming concepts: function, loop, variable, etc.
- Request assistance with coding problems

### Example Interactions

**You**: "I'm getting a syntax error in line 5"
**CodeBot**: "🤖 I can see your code. The syntax error is likely a missing closing parenthesis. Try adding ')' after the print statement on line 5."

**You**: "What's the best way to handle exceptions in Python?"
**CodeBot**: "🤖 For robust exception handling in Python, use try-except blocks with specific exception types. Here's a pattern: `try: risky_operation() except SpecificError as e: handle_error(e)`"

## 🎯 Key Features

### Smart Response System
- **Context Awareness**: Sees both chat messages and current code
- **Intelligent Triggering**: Only responds when helpful
- **Cooldown Protection**: Prevents spam with 15-second cooldowns
- **Natural Language**: Responds conversationally as a team member

### Visual Integration
- **AI Status Indicator**: Shows when CodeBot is active
- **Special Message Styling**: AI messages are clearly distinguished
- **🤖 Badge**: All AI messages show robot emoji
- **Seamless UI**: Integrates naturally with existing chat

### Technical Capabilities
- **Multi-Language Support**: Works with Python, JavaScript, Java, C++
- **Real-Time Processing**: Instant analysis of conversations and code
- **GPT-4o-mini Powered**: Uses OpenAI's efficient latest model
- **Socket Integration**: Real-time communication through WebSockets

## 🔧 Configuration

### Environment Variables
```bash
# Required
OPENAI_API_KEY=your-openai-api-key

# Optional (use defaults if not set)
FLASK_SECRET=your-flask-secret
JWT_SECRET=your-jwt-secret
```

### AI Behavior Settings
Edit `backend/src/services/ai_agent.py`:

```python
# Response timing
self.response_cooldown = 15  # Seconds between responses
self.min_messages_before_response = 3  # Messages needed before responding

# Context management  
self.max_context_messages = 10  # Chat history to keep
```

## 🎨 Customization

### Modify AI Personality
Edit the system prompt in `ai_agent.py`:

```python
system_prompt = f"""You are CodeBot, a helpful AI pair programming assistant.
Be encouraging, concise, and technically accurate.
Focus on practical solutions and code improvements."""
```

### Add Custom Keywords
Update trigger keywords:

```python
help_keywords = [
    'error', 'bug', 'problem', 'stuck', 'help',
    # Add your custom keywords
    'confused', 'optimization', 'performance'
]
```

### Style AI Messages
Modify `frontend/src/components/PairChat.vue`:

```css
.message.ai-message {
    background: linear-gradient(135deg, #10b981, #059669);
    /* Customize colors, borders, shadows */
}
```

## 🐛 Troubleshooting

### Common Issues

**AI Not Responding**
- Verify OpenAI API key is set correctly
- Check internet connection
- Look for errors in browser console

**Build Errors**
- Run `npm install` in frontend directory
- Check TypeScript compilation with `npm run type-check`

**Socket Issues**
- Ensure backend is running on port 5000
- Check CORS settings in `app.py`
- Verify WebSocket connections in browser dev tools

### Debug Mode
Enable detailed logging:

```python
# Add to ai_agent.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📊 Usage Analytics

The AI agent automatically tracks:
- Response frequency and timing
- Most common help topics
- Code context analysis
- User interaction patterns

Check console logs for debugging information.

## 🔒 Security

- **API Key Protection**: Never commit API keys to version control
- **Rate Limiting**: Built-in cooldowns prevent API abuse  
- **Content Filtering**: AI responses follow OpenAI's usage policies
- **Input Validation**: All user inputs are properly sanitized

## 🆘 Support

### Getting Help
1. Check the browser console for errors
2. Review backend logs for API issues
3. Verify environment variables are set
4. Test with simple programming questions first

### Feedback
The AI agent learns from interactions. Provide feedback by:
- Responding to AI suggestions in chat
- Mentioning what's helpful or not
- Reporting any inappropriate responses

## 🚀 Ready to Code!

Your AI-powered pair programming environment is now ready! CodeBot will assist you and your teammates with:

- ✅ Real-time programming help
- ✅ Code debugging assistance  
- ✅ Best practice suggestions
- ✅ Algorithm and syntax guidance
- ✅ Collaborative problem solving

Start coding and let CodeBot help make your pair programming sessions more productive! 🎉
