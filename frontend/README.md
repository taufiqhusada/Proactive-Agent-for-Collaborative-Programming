# Frontend

Vue 3 + TypeScript frontend for collaborative pair programming with AI assistance.

## Setup

1. **Install Node.js 18+**

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Configure environment variables:**
   
   Create a `.env` file in the root with:
   ```env
   VITE_API_URL=http://127.0.0.1:5000
   ```

## Development

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

## Production Build

```bash
npm run build
```

Build output will be in the `dist/` directory.

## Type Checking

```bash
npm run type-check
```

## Code Structure

- **`src/App.vue`** - Root application component
- **`src/views/`** - Page-level components
  - `LoginView.vue` - Authentication page
  - `PairRoomView.vue` - Main pair programming interface
- **`src/components/`** - Reusable UI components
  - `ChatContainer.vue` - Chat interface
  - `PairChat.vue` - Pair programming chat
  - `CodeRunner.vue` - Code execution
  - `AIAgentStatus.vue` - AI agent status display
  - `ScaffoldingPanel.vue` - Learning scaffolding UI
  - `CodeAnalysisPopup.vue` - Code analysis interface
  - `InterventionSettingsModal.vue` - AI settings
- **`src/composables/`** - Vue composition functions
  - `useCodeAnalysis.ts` - Code analysis logic
  - `useScaffolding.ts` - Scaffolding management
  - `useSocketHandlers.ts` - WebSocket event handling
  - `useReflectionSession.ts` - Reflection session logic
- **`src/stores/`** - Pinia state management
  - `useAuth.ts` - Authentication state
- **`src/lib/`** - Utility libraries
  - `socket.ts` - Socket.IO client setup
  - `runCode.ts` - Code execution utilities

## Deployment

### Vercel

```bash
./deploy-vercel.sh
```

Or manually:
```bash
vercel --prod
```

## Technologies

- **Vue 3** - Progressive JavaScript framework
- **TypeScript** - Type-safe JavaScript
- **Vite** - Fast build tool and dev server
- **CodeMirror 6** - Collaborative code editor
- **Socket.IO Client** - Real-time communication
- **Pinia** - State management
- **Bootstrap 5** - UI framework
