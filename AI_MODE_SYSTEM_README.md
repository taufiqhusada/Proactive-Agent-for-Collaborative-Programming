# AI Mode System - Individual vs Shared AI Assistant

This document describes the new AI mode functionality that allows users to choose between shared team AI collaboration and individual AI assistance.

## Overview

The system now supports two distinct AI interaction modes:

### 1. **Shared Mode (Default)**
- AI acts as a **team collaborator** visible to all users
- AI interventions appear in the shared team chat
- All team members see AI messages and responses
- Original behavior preserved for existing workflows

### 2. **Individual Mode (New)**
- AI acts as a **personal assistant** for each user
- Each user has their own private AI chat interface
- AI conversations are isolated and private to each user
- Team chat remains human-to-human only

## Architecture

### Frontend Components

#### 1. **AIModeToggle.vue**
- Location: `frontend/src/components/AIModeToggle.vue`
- Purpose: Allows users to switch between shared and individual AI modes
- Features:
  - Radio button interface for mode selection
  - Visual indicators for current mode
  - Real-time mode switching

#### 2. **IndividualAIChat.vue**
- Location: `frontend/src/components/IndividualAIChat.vue`
- Purpose: Private AI chat interface for individual mode
- Features:
  - Private conversation with AI assistant
  - Typing indicators
  - Message history
  - Responsive design

#### 3. **ChatContainer.vue**
- Location: `frontend/src/components/ChatContainer.vue`
- Purpose: Container that manages both chat modes
- Features:
  - Conditionally renders appropriate chat interface
  - Handles mode switching
  - Forwards events between components

#### 4. **Updated PairRoomView.vue**
- Replaced direct PairChat usage with ChatContainer
- Maintains backward compatibility
- Handles mode-specific message routing

### Frontend Services

#### 1. **aiModeService.ts**
- Location: `frontend/src/services/aiModeService.ts`
- Purpose: Manages AI mode state and configuration
- Features:
  - Mode state management
  - Channel name generation
  - Mode switching logic

### Backend Services

#### 1. **individual_ai_service.py**
- Location: `backend/src/services/individual_ai_service.py`
- Purpose: Handles individual AI conversations
- Features:
  - Per-user conversation management
  - Private AI response generation
  - Isolated conversation history

#### 2. **Updated app.py**
- Added socket handlers for individual AI mode
- Connection manager tracks user AI mode preferences
- Route individual messages to appropriate service

## Socket Events

### New Events

#### Frontend → Backend

1. **`ai_mode_changed`**
   ```json
   {
     "room": "room_id",
     "userId": "user_id", 
     "mode": "shared|individual",
     "channelName": "ai_channel_name"
   }
   ```

2. **`individual_ai_message`**
   ```json
   {
     "room": "room_id",
     "userId": "user_id",
     "message": "user_message",
     "messageId": "unique_id"
   }
   ```

#### Backend → Frontend

1. **`individual_ai_response`**
   ```json
   {
     "userId": "user_id",
     "response": "ai_response",
     "messageId": "original_message_id",
     "timestamp": "iso_timestamp"
   }
   ```

2. **`user_ai_mode_changed`**
   ```json
   {
     "userId": "user_id",
     "mode": "shared|individual"
   }
   ```

## Usage Instructions

### For Users

1. **Switching AI Modes**
   - Use the AI Mode Toggle in the right panel
   - Choose between "Team AI" (shared) or "Personal AI" (individual)
   - Mode change is immediate and persistent for the session

2. **Shared Mode**
   - AI messages appear in the main team chat
   - All team members see AI interactions
   - AI can intervene automatically based on conversation

3. **Individual Mode**
   - Team chat shows only human-to-human messages
   - Personal AI chat appears below team chat
   - Private conversations with AI assistant
   - Ask questions, get coding help, explanations, etc.

### For Developers

1. **Adding New AI Features**
   - Shared features: Modify `ai_agent_core.py` and related services
   - Individual features: Modify `individual_ai_service.py`
   - Both: Consider mode-specific behavior in frontend components

2. **Customizing AI Behavior**
   - Individual AI prompts: Edit `individual_ai_service.py` → `_generate_individual_response()`
   - Shared AI prompts: Edit existing AI agent services
   - UI behavior: Modify respective Vue components

## File Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── AIModeToggle.vue          # Mode selection UI
│   │   ├── IndividualAIChat.vue      # Individual AI chat
│   │   ├── ChatContainer.vue         # Chat mode manager
│   │   └── PairChat.vue             # Updated team chat
│   ├── services/
│   │   └── aiModeService.ts         # Mode management
│   └── views/
│       └── PairRoomView.vue         # Updated main view

backend/
├── src/
│   ├── services/
│   │   ├── individual_ai_service.py  # Individual AI logic
│   │   └── ai_agent_core.py         # Shared AI logic (existing)
│   └── app.py                       # Updated socket handlers
```

## Testing

### Manual Testing

1. **Mode Switching**
   - Join a room with multiple users
   - Switch between modes and verify UI changes
   - Confirm messages route correctly

2. **Individual AI**
   - Switch to individual mode
   - Send messages to AI assistant
   - Verify responses are private

3. **Shared AI**
   - Switch to shared mode
   - Trigger AI interventions
   - Verify all users see AI messages

### Automated Testing

Run the basic system test:
```bash
python test_ai_mode_system.py
```

## Configuration

### Environment Variables
- `OPENAI_API_KEY`: Required for both AI modes
- Existing AI configuration applies to both modes

### Default Behavior
- Users start in shared mode (preserves existing behavior)
- Mode preference is session-based (resets on page reload)
- Individual conversations are memory-based (clear on disconnect)

## Future Enhancements

1. **Persistent Mode Preferences**
   - Store user mode preference in database
   - Remember choice across sessions

2. **Advanced Individual AI Features**
   - Code analysis for individual users
   - Personal learning progress tracking
   - Custom AI personality settings

3. **Hybrid Mode**
   - Allow AI to operate in both modes simultaneously
   - Context-aware mode switching

4. **Analytics**
   - Track mode usage patterns
   - Measure AI effectiveness in different modes
   - User preference analytics

## Backward Compatibility

- Existing installations default to shared mode
- All existing AI features continue to work unchanged
- No breaking changes to existing APIs
- Progressive enhancement approach

## Support

For issues or questions about the AI mode system:
1. Check the test script output for basic functionality
2. Verify socket events are properly handled
3. Ensure OpenAI API key is configured
4. Review browser console for frontend errors
