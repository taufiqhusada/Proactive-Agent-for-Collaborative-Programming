# Proactive AI Agent for Collaborative Programming

A collaborative pair programming platform that integrates proactive AI assistance

## 🏗️ Architecture

The project consists of two main components:

- **Backend**: Flask-based API with Socket.IO for real-time collaboration
- **Frontend**: Vue 3 application with CodeMirror for collaborative code editing

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Node.js 18+
- MongoDB
- OpenAI API key

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy the example environment file and configure it:
   ```bash
   cp src/.env.example src/.env
   ```
   
   Then edit `src/.env` with your values:
   ```env
   OPENAI_API_KEY=your-openai-api-key
   MONGODB_URI=your-mongodb-uri  # Optional, for data tracking
   ```

4. Run the backend server:
   ```bash
   flask --app src/app run
   ```
   

The backend will run on `http://127.0.0.1:5000` by default.

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Create a `.env` file with the backend URL:
   ```env
   VITE_API_URL=http://127.0.0.1:5000
   ```

4. Start the development server:
   ```bash
   npm run dev
   ```


## 📁 Project Structure

```
.
├── backend/
│   ├── src/
│   │   ├── app.py                    # Main Flask application
│   │   ├── config/
│   │   │   └── openai_connector.py   # OpenAI API configuration
│   │   ├── database/
│   │   │   ├── db.py                 # Database connection
│   │   │   └── models.py             # Database models
│   │   ├── routes/                   # API route handlers
│   │   └── services/
│   │       ├── ai_agent.py           # Core AI agent logic
│   │       ├── ai_intervention.py    # Intervention strategies
│   │       ├── ai_code_analysis.py   # Code analysis service
│   │       ├── ai_reflection.py      # Reflection facilitation
│   │       ├── scaffolding_service.py # Learning scaffolding
│   │       └── individual_ai_service.py # Individual AI assistance
│   ├── requirements.txt
│   └── Dockerfile
│
└── frontend/
    ├── src/
    │   ├── App.vue                   # Root component
    │   ├── main.ts                   # Application entry point
    │   ├── components/
    │   │   ├── ChatContainer.vue     # Chat interface
    │   │   ├── CodeRunner.vue        # Code execution
    │   │   ├── PairChat.vue          # Pair programming chat
    │   │   ├── ScaffoldingPanel.vue  # AI scaffolding UI
    │   │   ├── CodeAnalysisPopup.vue # Code analysis UI
    │   │   └── AIAgentStatus.vue     # AI agent status
    │   ├── composables/
    │   │   ├── useCodeAnalysis.ts    # Code analysis logic
    │   │   ├── useScaffolding.ts     # Scaffolding logic
    │   │   └── useSocketHandlers.ts  # WebSocket handlers
    │   ├── views/
    │   │   ├── LoginView.vue         # Login page
    │   │   └── PairRoomView.vue      # Main pair programming view
    │   └── stores/
    │       └── useAuth.ts            # Authentication state
    ├── package.json
    └── vite.config.ts
```

### Backend
- Flask - Web framework
- Flask-SocketIO - Real-time communication
- OpenAI API - AI-powered assistance
- MongoDB - Database
- Gunicorn - Production server

### Frontend
- Vue 3 - Frontend framework
- TypeScript - Type-safe JavaScript
- CodeMirror 6 - Collaborative code editor
- Socket.IO Client - Real-time communication
- Vite - Build tool
- Pinia - State management


## 📧 Contact
taufiq.daryanto@gmail.com
