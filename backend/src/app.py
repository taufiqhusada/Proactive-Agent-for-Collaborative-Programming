"""
app.py - Backend for remote pair programming
"""

import os
import sys
import subprocess
import threading
import time
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from services.ai_agent import init_ai_agent, get_ai_agent
from services.scaffolding_service import ScaffoldingService
from services.individual_ai_service import init_individual_ai_service, get_individual_ai_service
from database.db import init_db, close_db
from database.models import CodeExecution

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET", "change-me")
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET", "change-me-too")
CORS(app, supports_credentials=True)
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    logger=False,  # Disable verbose logging
    engineio_logger=False,  # Disable engine.io detailed logging
    # async_mode="threading",  # Use threading instead of eventlet in local development
    async_mode="eventlet", # this is for GCP deployment
    # Support both transports for better compatibility
    transports=['websocket', 'polling'],
    # Better timeout settings to prevent idle disconnections
    ping_timeout=120,  # Wait 2 minutes for pong response  
    ping_interval=20,  # Send ping every 20 seconds
)
jwt = JWTManager(app)

class ConnectionManager:
    """Track who's in which Socket.IO room and store room state."""
    def __init__(self):
        self.rooms = {}      # room_id -> set(sid)
        self.room_state = {} # room_id -> { code: str, language: str }
        self.user_names = {} # sid -> username mapping
        self.session_states = {} # room_id -> { started: bool, ai_mode: str, locked: bool }

    def join(self, sid: str, room: str, username: str = None):
        self.rooms.setdefault(room, set()).add(sid)
        if username:
            self.user_names[sid] = username
        # Initialize session state if not exists
        if room not in self.session_states:
            self.session_states[room] = {
                'started': False,
                'ai_mode': 'shared',
                'locked': False
            }

    def leave(self, sid: str, room: str):
        self.rooms.get(room, set()).discard(sid)
        if room in self.rooms and not self.rooms[room]:
            self.rooms.pop(room, None)
            self.room_state.pop(room, None)
            self.session_states.pop(room, None)
        # Clean up username when user leaves
        self.user_names.pop(sid, None)

    def get_username(self, sid: str):
        return self.user_names.get(sid, f"User {sid[-4:]}")

    def get_room_state(self, room: str):
        return self.room_state.get(room, {"code": 'print("Hello")', "language": "python"})

    def set_session_started(self, room: str, started: bool):
        """Set session started state without locking AI mode"""
        if room not in self.session_states:
            self.session_states[room] = {
                'started': False,
                'ai_mode': 'shared',
                'locked': False
            }
        self.session_states[room]['started'] = started
        # Remove AI mode locking - users can change mode anytime
        
    def is_session_started(self, room: str):
        """Check if session is started for a room"""
        return self.session_states.get(room, {}).get('started', False)
        
    def is_ai_mode_locked(self, room: str):
        """Check if AI mode is locked for a room"""
        return self.session_states.get(room, {}).get('locked', False)
        
    def set_ai_mode(self, room: str, mode: str):
        """Set AI mode for a room - always allowed"""
        if room not in self.session_states:
            self.session_states[room] = {
                'started': False,
                'ai_mode': 'shared',
                'locked': False
            }
        self.session_states[room]['ai_mode'] = mode
        return True  # Always successful
    
    def get_ai_mode(self, room: str):
        """Get the current AI mode for a room"""
        return self.session_states.get(room, {}).get('ai_mode', 'shared')

    def set_room_state(self, room: str, code: str, language: str = "python"):
        self.room_state[room] = {"code": code, "language": language}

manager = ConnectionManager()

# Initialize AI Agent, Scaffolding Service, Individual AI Service, and Reflection Service
ai_agent = init_ai_agent(socketio)
scaffolding_service = ScaffoldingService()
individual_ai_service = init_individual_ai_service(socketio)

# Initialize Database
init_db()

# Initialize Reflection Service
from services.ai_reflection import init_reflection_service
reflection_service = init_reflection_service(socketio)

# Track active scaffolding requests to prevent duplicates
active_scaffolding_requests = {}  # {comment_id: {'timestamp': time, 'user_id': request.sid}}
SCAFFOLDING_LOCK_TIMEOUT = 10  # seconds

def cleanup_expired_scaffolding_locks():
    """Remove expired scaffolding locks"""
    current_time = time.time()
    expired_keys = []
    
    for comment_id, lock_info in active_scaffolding_requests.items():
        if current_time - lock_info['timestamp'] > SCAFFOLDING_LOCK_TIMEOUT:
            expired_keys.append(comment_id)
    
    for key in expired_keys:
        print(f"🧹 Cleaning up expired scaffolding lock: {key}")
        del active_scaffolding_requests[key]

def create_comment_id(comment_line, cursor_line, language):
    """Create a unique identifier for a scaffolding request"""
    return f"{language}:{cursor_line}:{comment_line.strip()}"

# WebSocket handlers
@socketio.on("connect", namespace="/ws")
def ws_connect():
    print(f"WS client {request.sid} connected")

@socketio.on("join", namespace="/ws")
def ws_join(data):
    room = data["room"]
    username = data.get("username", "Guest")  # Get username from client
    current_code = data.get("current_code", None)  # Get current code from frontend
    current_language = data.get("current_language", "python")  # Get current language from frontend
    
    join_room(room)
    manager.join(request.sid, room, username)
    
    # Get current room state
    room_state = manager.get_room_state(room)
    current_user_count = len(manager.rooms.get(room, set()))
    print(f"Client {request.sid} ({username}) joined room {room}, sending state. Users in room: {current_user_count}")
    
    # If this is the first user and they have code, use their code instead of default
    if current_user_count == 1 and current_code is not None and current_code.strip() != 'print("Hello")':
        print(f"First user joined with existing code, updating room state from default")
        manager.set_room_state(room, current_code, current_language)
        room_state = manager.get_room_state(room)  # Get updated state
    
    # AI agent joins the room when first user joins
    if current_user_count == 1:
        ai_agent.join_room(room)
    
    # Notify ALL users (including self) about the updated user count
    emit("user_count_update", {
        "userCount": current_user_count
    }, room=room, include_self=True)
    
    # Notify other users that someone joined (excluding self)
    emit("user_joined", {
        "userId": request.sid, 
        "username": username,
        "userCount": current_user_count
    }, room=room, include_self=False)
    
    return {"code": room_state["code"]}

@socketio.on("leave", namespace="/ws") 
def ws_leave(data):
    room = data["room"]
    username = manager.get_username(request.sid)  # Get stored username
    leave_room(room)
    manager.leave(request.sid, room)
    
    # Get updated user count
    current_user_count = len(manager.rooms.get(room, set()))
    
    # Notify ALL remaining users about the updated user count
    emit("user_count_update", {
        "userCount": current_user_count
    }, room=room, include_self=False)
    
    # Notify other users that someone left
    emit("user_left", {
        "userId": request.sid,
        "username": username,
        "userCount": current_user_count
    }, room=room, include_self=False)

@socketio.on("update", namespace="/ws")
def ws_update(data):
    """
    Forward code updates to everyone else in the room.
    """
    print(f"WS update from {request.sid} in room {data['room']}")
    room = data["room"]
    delta = data["delta"]
    source_id = data.get("sourceId", request.sid)
    
    # Store the updated code in room state
    manager.set_room_state(room, delta)
    
    # Update AI agent with new code context
    ai_agent.handle_code_update(room, delta, "python")
    
    # Broadcast to all other clients in the room
    emit("update", {"delta": delta, "sourceId": source_id}, room=room, include_self=False)

@socketio.on("cursor", namespace="/ws")
def ws_cursor(data):
    """
    Forward cursor position/selection to everyone else in the room.
    """
    print(f"WS cursor from {request.sid} in room {data['room']}")
    room = data["room"]
    
    # Broadcast cursor position to all other clients in the room
    emit("cursor", data, room=room, include_self=False)

@socketio.on("selection", namespace="/ws")
def ws_selection(data):
    """
    Forward text selection/highlighting to everyone else in the room.
    """
    print(f"WS selection from {request.sid} in room {data['room']}")
    room = data["room"]
    
    # Broadcast selection to all other clients in the room
    emit("selection", data, room=room, include_self=False)

@socketio.on("chat_message", namespace="/ws")
def ws_chat_message(data):
    """
    Forward chat messages to everyone else in the room and process with AI agent.
    """
    print(f"WS chat message from {request.sid} in room {data['room']}")
    room = data["room"]
    
    # Broadcast chat message - include self for system messages, exclude for regular messages
    include_self = data.get('isSystem', False)
    emit("chat_message", data, room=room, include_self=include_self)
    
    # Check AI mode before processing with AI agent
    current_ai_mode = manager.get_ai_mode(room)
    
    # Only process with AI if not in 'none' mode
    if current_ai_mode != 'none':
        # Process message with AI agent in a separate thread
        def process_ai_message():
            print(f"🤖 Processing AI message for room {room} (mode: {current_ai_mode})")
            ai_agent.process_message_sync(data)
            print(f"🤖 AI message processing completed for room {room}")
        
        threading.Thread(target=process_ai_message, daemon=True).start()
    else:
        print(f"🚫 Skipping AI processing for room {room} - AI mode is 'none'")

@socketio.on("ai_mode_changed", namespace="/ws")
def ws_ai_mode_changed(data):
    """
    Handle AI mode changes and broadcast to all users in the room.
    """
    print(f"🔄 AI mode change requested to {data['mode']} by user {data['changedBy']} in room {data['roomId']}")
    room = data["roomId"]
    
    # Set the AI mode (always allowed now)
    manager.set_ai_mode(room, data["mode"])
    
    # Broadcast the mode change to all users in the room (including sender for confirmation)
    emit("ai_mode_changed", {
        "mode": data["mode"],
        "changedBy": data["changedBy"]
    }, room=room)
    
    print(f"📡 AI mode change to {data['mode']} accepted and broadcasted to room {room}")

@socketio.on("problem_update", namespace="/ws")
def ws_problem_update(data):
    """
    Handle problem description updates and notify AI agent.
    """
    print(f"Problem update from {request.sid} in room {data['room']}")
    room = data["room"]
    problem_title = data.get("problemTitle", "")
    problem_description = data.get("problemDescription", "")
    
    # Update AI agent with new problem context
    ai_agent.handle_problem_update(room, problem_title, problem_description)
    
    # Optionally broadcast to other clients in the room
    emit("problem_update", {
        "problemTitle": problem_title,
        "problemDescription": problem_description
    }, room=room, include_self=False)

@socketio.on("ai_audio_playback_complete", namespace="/ws")
def ws_ai_audio_playback_complete(data):
    """
    Handle notification from frontend that AI audio playback is complete.
    This is when we should release the AI generation lock.
    """
    print(f"AI audio playback complete notification from {request.sid} in room {data['room']}")
    room = data["room"]
    message_id = data.get("messageId", "")
    
    # Release AI generation lock now that audio is actually finished
    ai_agent.release_generation_lock(room, message_id)

@socketio.on("code_execution", namespace="/ws")
def ws_code_execution(data):
    """
    Handle code execution events for real-time collaboration and AI analysis.
    """
    print(f"Code execution event from {request.sid} in room {data['room']}")
    room = data["room"]
    code = data.get("code", "")
    language = data.get("language", "python")
    result = data.get("result", {})
    
    # Broadcast execution result to other clients in the room
    emit("code_execution_result", {
        "code": code,
        "language": language,
        "result": result,
        "timestamp": time.time(),
        "user_id": request.sid
    }, room=room, include_self=False)
    
    # Trigger AI validation in background (already handled by API endpoint)
    print(f"🤖 Code execution broadcasted to room {room}")

@socketio.on("voice_activity_detected", namespace="/ws")
def ws_voice_activity_detected(data):
    """
    Handle voice activity detection from frontend to cancel pending timers.
    Frontend decides what type of timer to cancel.
    """
    print(f"🎤 === VOICE ACTIVITY EVENT RECEIVED ===")
    print(f"🎤 Data: {data}")
    
    room = data["room"]
    user_id = data["userId"]
    event_type = data["event"]  # 'speechstart' or 'speechend'
    timer_type = data.get("timer_type", "ai_agent")  # 'ai_agent' or 'reflection'
    
    print(f"🎤 Voice activity: {event_type} from user {user_id} in room {room}, timer_type: {timer_type}")
    
    print(f"🚫 Attempting to cancel pending AI agent timers due to voice activity in room {room}")

    # Stateless timer cancellation - only check if timer exists
    if room in ai_agent.pending_timers:
        ai_agent._cancel_pending_intervention(room, "voice activity detected")
        print(f"✅ Successfully cancelled pending AI agent timer due to voice activity in room {room}")
    else:
        available_timers = list(ai_agent.pending_timers.keys())
        print(f"🔍 No pending AI agent timer to cancel in room {room}. Available timers: {available_timers}")

@socketio.on("chat_typing_activity", namespace="/ws")
def ws_chat_typing_activity(data):
    """
    Handle chat typing activity detection from frontend to cancel pending timers.
    Frontend decides what type of timer to cancel.
    """
    room = data["room"]
    user_id = data["userId"]
    event_type = data["event"]  # 'typing_start'
    timer_type = data.get("timer_type", "ai_agent")  # 'ai_agent' or 'reflection'
    
    print(f"⌨️  Chat typing: {event_type} from user {user_id} in room {room}, timer_type: {timer_type}")
    
    print(f"🚫 Attempting to cancel pending AI agent timers due to chat typing activity in room {room}")
    
    # Stateless timer cancellation - only check if timer exists
    if room in ai_agent.pending_timers:
        ai_agent._cancel_pending_intervention(room, "chat typing activity detected")
        print(f"✅ Successfully cancelled pending AI agent timer due to chat typing in room {room}")
    else:
        available_timers = list(ai_agent.pending_timers.keys())
        print(f"🔍 No pending AI agent timer to cancel in room {room}. Available timers: {available_timers}")

@socketio.on("disconnect", namespace="/ws")
def ws_disconnect():
    print(f"WS client {request.sid} disconnected")
    # Notify other users when someone disconnects
    for room in list(manager.rooms.keys()):
        if request.sid in manager.rooms.get(room, set()):
            username = manager.get_username(request.sid)  # Get stored username
            manager.leave(request.sid, room)
            current_user_count = len(manager.rooms.get(room, set()))
            
            # Notify remaining users about updated count and disconnection
            emit("user_count_update", {
                "userCount": current_user_count
            }, room=room, include_self=False)
            
            emit("user_disconnected", {
                "userId": request.sid,
                "username": username,
                "userCount": current_user_count
            }, room=room, include_self=False)


# Reflection toggle handler
@socketio.on("toggle_reflection", namespace="/ws")
def ws_toggle_reflection(data):
    """Handle reflection session toggle (start/stop)"""
    try:
        room = data.get("room")
        action = data.get("action")  # "start" or "stop"
        
        if not room:
            print("❌ Toggle reflection: No room specified")
            return
        
        print(f"🎓 Reflection toggle request: {action} for room {room}")
        
        # Import reflection service
        from services.ai_reflection import get_reflection_service
        reflection_service = get_reflection_service()
        
        if not reflection_service:
            print("❌ Toggle reflection: Reflection service not available")
            emit("reflection_error", {
                "message": "Reflection service not available"
            }, room=room)
            return
        
        if action == "start":
            # Get current room state for reflection context
            room_state = manager.get_room_state(room)
            current_code = room_state.get("code", "")
            language = room_state.get("language", "python")
            
            # Start reflection session
            session_id = reflection_service.start_reflection_session(
                room_id=room,
                final_code=current_code,
                language=language,
                problem_description="Current coding session",
                chat_history=[]  # Could enhance this with actual chat history
            )
            
            if session_id:
                print(f"✅ Started reflection session {session_id}")
                # Broadcast reflection started to all users
                emit("session_state_changed", {
                    'action': 'reflection_started',
                    'room': room,
                    'session_id': session_id,
                    'message': 'Reflection session started'
                }, room=room)
            else:
                print("❌ Failed to start reflection session")
                
        elif action == "stop":
            # End reflection session for this room
            success = reflection_service.end_reflection_session_by_room(room)
            if success:
                print(f"✅ Stopped reflection session for room {room}")
                # Broadcast reflection stopped to all users
                emit("session_state_changed", {
                    'action': 'reflection_stopped',
                    'room': room,
                    'message': 'Reflection session ended'
                }, room=room)
            else:
                print(f"❌ No active reflection session found for room {room}")
                
    except Exception as e:
        print(f"❌ Error toggling reflection: {e}")
        emit("reflection_error", {
            "message": f"Error toggling reflection: {str(e)}"
        }, room=data.get("room"))

# REST API
@app.route("/", methods=["GET"])
def root():
    return "Hello, Remote Pair Programming!"

@app.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint for monitoring and load balancers
    """
    try:
        # Basic health check - you can add more sophisticated checks here
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "service": "hhai-pair-programming-backend"
        }
        
        # Optional: Add database connectivity check
        # try:
        #     # Add your database ping here if needed
        #     pass
        # except Exception as e:
        #     health_status["database"] = "error"
        #     health_status["database_error"] = str(e)
        
        return jsonify(health_status), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }), 500

@app.route("/api/login", methods=["POST"])
def login():
    """
    Accept JSON {"username": ..., "password": ...}
    Returns {"access_token": "..."} for JWT-secured routes.
    """
    user = request.json.get("username", "guest")
    access = create_access_token(identity=user)
    return jsonify(access_token=access)

@app.route("/api/individual-ai", methods=["POST"])
def individual_ai_chat():
    """
    Handle individual AI assistant messages via REST API.
    Accepts JSON: {
        "userId": "user_id",
        "roomId": "room_id", 
        "message": "user_message"
    }
    Returns JSON: {
        "response": "ai_response",
        "timestamp": "iso_timestamp"
    }
    """
    try:
        data = request.json
        user_id = data.get("userId")
        room_id = data.get("roomId")
        message = data.get("message")
        
        if not all([user_id, room_id, message]):
            return jsonify({
                "error": "Missing required fields: userId, roomId, message"
            }), 400
        
        # Check AI mode for the room
        current_ai_mode = manager.get_ai_mode(room_id)
        if current_ai_mode == 'none':
            print(f"🚫 Individual AI disabled - AI mode is 'none' for room {room_id}")
            return jsonify({
                "error": "AI assistance is disabled for this room",
                "aiModeDisabled": True
            }), 403
        
        if current_ai_mode != 'individual':
            print(f"🚫 Individual AI not available - AI mode is '{current_ai_mode}' for room {room_id}")
            return jsonify({
                "error": "Individual AI mode is not active for this room",
                "wrongMode": True,
                "currentMode": current_ai_mode
            }, 403)
        
        # Get AI response synchronously
        ai_response = individual_ai_service.handle_individual_message_sync(
            user_id, room_id, message
        )
        
        if ai_response:
            return jsonify({
                "response": ai_response,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "error": "Failed to generate AI response"
            }), 500
            
    except Exception as e:
        print(f"❌ Error in individual AI endpoint: {e}")
        return jsonify({
            "error": "Internal server error"
        }), 500

@app.route("/api/run", methods=["POST"])
@jwt_required()
def run_code():
    """
    POST {"lang": "python", "code": "print(1+1)"}
    NOTE: **unsafe** - sandbox properly in production.
    """
    code = request.json.get("code", "")
    proc = subprocess.run(
        ["python", "-c", code],
        capture_output=True, text=True, timeout=5
    )
    return jsonify(stdout=proc.stdout, stderr=proc.stderr)

@app.route('/api/run-code', methods=['POST'])
def execute_code_endpoint():
    """Execute code in specified language and return output"""
    try:
        data = request.json
        code = data.get('code', '')
        language = data.get('language', 'python')
        room_id = data.get('room_id')  # Get room_id for AI validation
        
        print(f"🚀 Code Execution Request:")
        print(f"  Language: {language}")
        print(f"  Room ID: {room_id}")
        print(f"  Code: {code[:100]}...")
        
        if not code.strip():
            return jsonify({'error': 'No code provided'}), 400
        
        # Execute code based on language
        result = execute_code(code, language)
        
        # Save code execution to database
        if room_id:
            try:
                code_execution = CodeExecution(
                    room_id=room_id,
                    code=code,
                    language=language,
                    timestamp=datetime.utcnow(),
                    execution_output=result.get('output', ''),
                    execution_error=result.get('error', ''),
                    execution_time_ms=int(result.get('executionTime', 0))
                )
                code_execution.save()
                print(f"💾 Saved code execution to database for room {room_id}")
            except Exception as db_error:
                print(f"⚠️  Database save error (non-blocking): {db_error}")
        
        # Trigger panel analysis for execution feedback (non-blocking)
        if room_id and ai_agent and code.strip():
            try:
                ai_agent.start_panel_analysis(room_id, code, result)
                print(f"🔍 Started panel analysis for room {room_id}")
            except Exception as analysis_error:
                print(f"⚠️  Panel analysis error (non-blocking): {analysis_error}")
        
        print(f"✅ Execution Result: {result}")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error executing code: {e}")
        return jsonify({'error': str(e)}), 500

def execute_code(code, language):
    """Execute code in the specified language"""
    import tempfile
    import os
    import subprocess
    import time
    
    start_time = time.time()
    
    try:
        if language == 'python':
            # Execute Python code
            proc = subprocess.run(
                ["python", "-c", code],
                capture_output=True, 
                text=True, 
                timeout=10,
                cwd=tempfile.gettempdir()
            )
            
        elif language == 'javascript':
            # Execute JavaScript code using Node.js
            proc = subprocess.run(
                ["node", "-e", code],
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
        elif language == 'java':
            # Execute Java code
            with tempfile.NamedTemporaryFile(suffix=".java", delete=False) as source_file:
                source_file.write(code.encode())
                source_file.flush()
                
                class_name = os.path.basename(source_file.name)[:-5]  # Remove .java extension
                jar_file = source_file.name + ".jar"
                
                # Compile and package as JAR
                compile_proc = subprocess.run(
                    ["javac", source_file.name, "-d", tempfile.gettempdir()],
                    capture_output=True, text=True
                )
                
                if compile_proc.returncode != 0:
                    return {
                        'output': '',
                        'error': compile_proc.stderr,
                        'exitCode': compile_proc.returncode,
                        'executionTime': 0
                    }
                
                # Execute the compiled Java class
                proc = subprocess.run(
                    ["java", "-cp", tempfile.gettempdir(), class_name],
                    capture_output=True, text=True, timeout=10
                )
                
                # Clean up class and JAR files
                try:
                    os.remove(os.path.join(tempfile.gettempdir(), class_name + ".class"))
                    os.remove(jar_file)
                except:
                    pass
            
        elif language == 'c':
            # Execute C code
            try:
                with tempfile.NamedTemporaryFile(suffix=".c", delete=False) as source_file:
                    source_file.write(code.encode())
                    source_file.flush()
                    
                    cpp_file = source_file.name
                    exe_file = cpp_file[:-2]  # Remove .c extension for executable
                    
                    # Compile the C code
                    compile_proc = subprocess.run(
                        ["gcc", cpp_file, "-o", exe_file],
                        capture_output=True, text=True
                    )
                    
                    if compile_proc.returncode != 0:
                        return {
                            'output': '',
                            'error': compile_proc.stderr,
                            'exitCode': compile_proc.returncode,
                            'executionTime': 0
                        }
                    
                    # Execute the compiled program
                    proc = subprocess.run(
                        [exe_file],
                        capture_output=True, text=True, timeout=10
                    )
                    
            finally:
                # Clean up
                try:
                    os.unlink(cpp_file)
                    os.unlink(exe_file)
                except:
                    pass
                    
        else:
            return {
                'output': '',
                'error': f'Unsupported language: {language}',
                'exitCode': 1,
                'executionTime': 0
            }
        
        execution_time = (time.time() - start_time) * 1000
        
        return {
            'output': proc.stdout,
            'error': proc.stderr,
            'exitCode': proc.returncode,
            'executionTime': execution_time
        }
        
    except subprocess.TimeoutExpired:
        return {
            'output': '',
            'error': 'Execution timeout (10 seconds)',
            'exitCode': 124,
            'executionTime': 10000
        }
    except Exception as e:
        return {
            'output': '',
            'error': str(e),
            'exitCode': 1,
            'executionTime': (time.time() - start_time) * 1000
        }

@app.route('/api/analyze-code-block', methods=['POST'])
def analyze_code_block():
    """Analyze a code block for potential issues and suggestions"""
    try:
        data = request.json
        code = data.get('code', '')
        language = data.get('language', 'python')
        context = data.get('context', {})
        problem_context = data.get('problemContext', None)
        room_id = data.get('roomId', None)  # Get room ID for socket broadcasting

        print(f"📊 Code Analysis Request:")
        print(f"  Code: {code[:100]}...")
        print(f"  Language: {language}")
        print(f"  Context: {context}")
        print(f"  Room ID: {room_id}")
        # print(f"  Problem Context: {problem_context}")
        
        if not code.strip():
            return jsonify({'issues': []})
        
        # Use AI agent to analyze the code with problem context
        analysis = ai_agent.analyze_code_block(code, language, context, problem_context)
        
        result = {
            'issues': analysis.get('issues', []),
            'suggestions': analysis.get('suggestions', []),
            'timestamp': analysis.get('timestamp'),
            'confidence': analysis.get('confidence', 'medium')
        }

        print("this is the result", result)
        
        # Always broadcast results to all users in the room (whether issues found or not)
        if room_id:
            print(f"📡 Broadcasting code analysis results to room {room_id}")
            
            # Determine the highest severity level
            issues = result.get('issues', [])
            highest_severity = 'medium'
            if issues:
                severity_priority = {'high': 3, 'medium': 2, 'low': 1}
                highest_severity = max(issues, key=lambda x: severity_priority.get(x.get('severity', 'medium'), 0)).get('severity', 'medium')
            
            # Prepare code block info for frontend
            code_block = {
                'code': code,
                'language': language,
                'startLine': context.get('startLine'),
                'endLine': context.get('endLine'),
                'cursorLine': context.get('cursorLine')
            }
            
            # Broadcast to all users in the room via socket
            socketio.emit('code_analysis_result', {
                'codeBlock': code_block,
                'issues': issues,
                'highestSeverity': highest_severity,
                'timestamp': result.get('timestamp'),
                'confidence': result.get('confidence')
            }, room=room_id, namespace='/ws')
            
            print(f"✅ Code analysis results broadcasted to room {room_id} (issues: {len(issues)})")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error analyzing code block: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset-ai-state', methods=['POST'])
def reset_ai_state():
    """Reset AI agent state for a specific room"""
    try:
        data = request.json
        room_id = data.get('room_id')
        
        if not room_id:
            return jsonify({'error': 'room_id is required'}), 400
        
        print(f"🔄 Resetting AI state for room: {room_id}")
        
        # Get state summary before reset (for debugging)
        state_before = ai_agent.get_room_state_summary(room_id)
        
        # Reset the AI agent state
        ai_agent.reset_room_state(room_id)
        
        # Reset session state and unlock AI mode
        manager.set_session_started(room_id, False)
        
        # Also end any active reflection sessions for this room
        from services.ai_reflection import get_reflection_service
        reflection_service = get_reflection_service()
        if reflection_service:
            success = reflection_service.end_reflection_session_by_room(room_id)
            if success:
                print(f"✅ Ended active reflection session for room {room_id} during reset")
            else:
                print(f"ℹ️ No active reflection session found for room {room_id}")
        
        # Get state summary after reset
        state_after = ai_agent.get_room_state_summary(room_id)
        
        # Broadcast session reset to all users in the room
        socketio.emit('session_state_changed', {
            'action': 'session_reset',
            'room': room_id,
            'message': 'Session and reflection reset'
        }, room=room_id, namespace='/ws')
        
        return jsonify({
            'success': True,
            'message': f'AI state reset for room {room_id}',
            'state_before': state_before,
            'state_after': state_after
        })
        
    except Exception as e:
        print(f"Error resetting AI state: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-ai-state', methods=['GET'])
def get_ai_state():
    """Get current AI agent state for a specific room (for debugging)"""
    try:
        room_id = request.args.get('room_id')
        
        if not room_id:
            return jsonify({'error': 'room_id parameter is required'}), 400
        
        state_summary = ai_agent.get_room_state_summary(room_id)
        
        return jsonify({
            'success': True,
            'room_id': room_id,
            'state': state_summary
        })
        
    except Exception as e:
        print(f"Error getting AI state: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-scaffolding', methods=['POST'])
def generate_scaffolding():
    """Generate code scaffolding using LLM based on user comments"""
    try:
        data = request.json
        code = data.get('code', '')
        language = data.get('language', 'python')
        cursor_line = data.get('cursorLine', 0)
        room_id = data.get('roomId')
        
        print(f"🏗️  Scaffolding Request:")
        print(f"  Language: {language}")
        print(f"  Cursor Line: {cursor_line}")
        print(f"  Room ID: {room_id}")
        
        # Check AI mode if room_id is provided
        if room_id:
            current_ai_mode = manager.get_ai_mode(room_id)
            if current_ai_mode == 'none':
                print(f"🚫 Scaffolding disabled - AI mode is 'none' for room {room_id}")
                return jsonify({
                    'hasScaffolding': False,
                    'message': 'Scaffolding disabled - No AI mode is active'
                })
            print(f"✅ Scaffolding allowed - AI mode is '{current_ai_mode}' for room {room_id}")
        else:
            print("⚠️ No room ID provided, proceeding with scaffolding")
        
        # Clean up expired locks first
        cleanup_expired_scaffolding_locks()
        
        # Get the comment line
        lines = code.split('\n')
        if cursor_line >= len(lines):
            return jsonify({
                'hasScaffolding': False,
                'message': 'Invalid cursor line'
            })
        
        comment_line = lines[cursor_line]
        
        # Create unique identifier for this scaffolding request
        comment_id = create_comment_id(comment_line, cursor_line, language)
        current_time = time.time()
        
        # Check if this comment is already being processed
        if comment_id in active_scaffolding_requests:
            existing_lock = active_scaffolding_requests[comment_id]
            time_since_lock = current_time - existing_lock['timestamp']
            
            if time_since_lock < SCAFFOLDING_LOCK_TIMEOUT:
                print(f"🚫 Scaffolding already in progress for: {comment_line.strip()}")
                return jsonify({
                    'hasScaffolding': False,
                    'message': 'Scaffolding already in progress for this comment',
                    'isLocked': True,
                    'lockHolder': existing_lock['user_id'],
                    'timeRemaining': SCAFFOLDING_LOCK_TIMEOUT - time_since_lock
                })
        
        # Acquire lock for this scaffolding request
        active_scaffolding_requests[comment_id] = {
            'timestamp': current_time,
            'user_id': request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        }
        
        print(f"🔒 Acquired scaffolding lock for: {comment_line.strip()}")
        
        try:
            # Use LLM to generate scaffolding
            result = scaffolding_service.generate_scaffolding(comment_line, language, code)
            
            if not result:
                # Release lock on no scaffolding
                if comment_id in active_scaffolding_requests:
                    del active_scaffolding_requests[comment_id]
                    
                return jsonify({
                    'hasScaffolding': False,
                    'message': 'No scaffolding pattern detected for this comment'
                })
            
            # Add line number info for replacement
            result['replaceLineRange'] = {
                'start': cursor_line,
                'end': cursor_line + 1
            }
            
            print(f"✅ Generated scaffolding using LLM")
            
            # Release lock on success
            if comment_id in active_scaffolding_requests:
                del active_scaffolding_requests[comment_id]
                
            return jsonify(result)
            
        except Exception as scaffolding_error:
            # Release lock on error
            if comment_id in active_scaffolding_requests:
                del active_scaffolding_requests[comment_id]
            raise scaffolding_error
        
    except Exception as e:
        print(f"❌ Error generating scaffolding: {e}")
        return jsonify({
            'error': str(e),
            'hasScaffolding': False
        }), 500

# Session control endpoints
@app.route('/api/start-session', methods=['POST'])
def start_session():
    """Start a pair programming session"""
    try:
        data = request.get_json()
        room_id = data.get('room_id')
        
        if not room_id:
            return jsonify({'success': False, 'error': 'Room ID is required'}), 400
        
        print(f"🚀 Starting session for room {room_id}")
        
        # Mark session as started and lock AI mode
        manager.set_session_started(room_id, True)
        
        # Send Bob greeting for session start only if AI is enabled
        current_ai_mode = manager.get_ai_mode(room_id)
        if current_ai_mode != 'none':
            ai_agent.send_session_start_greeting(room_id)
            print(f"🤖 AI greeting sent for mode: {current_ai_mode}")
        else:
            print(f"🚫 Skipping AI greeting - AI mode is 'none'")
        
        # Broadcast session started to all users in the room
        socketio.emit('session_state_changed', {
            'action': 'session_started',
            'room': room_id,
            'message': 'Session started',
            'ai_mode': current_ai_mode
        }, room=room_id, namespace='/ws')
        
        return jsonify({
            'success': True, 
            'message': f'Session started for room {room_id}'
        })
        
    except Exception as e:
        print(f"❌ Error starting session: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/intervention-settings', methods=['GET'])
def get_intervention_settings():
    """Get current intervention settings"""
    try:
        settings = ai_agent.intervention_service.get_intervention_settings()
        return jsonify({
            'success': True,
            'settings': settings
        })
    except Exception as e:
        print(f"❌ Error getting intervention settings: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/intervention-settings', methods=['POST'])
def update_intervention_settings():
    """Update intervention settings"""
    try:
        data = request.get_json()
        if not data or 'settings' not in data:
            return jsonify({'success': False, 'error': 'Missing settings data'}), 400
        
        settings = data['settings']
        
        # Validate settings
        valid_keys = {'idle_intervention_enabled', 'idle_intervention_delay', 'progress_check_enabled', 'progress_check_interval'}
        for key in settings:
            if key not in valid_keys:
                return jsonify({'success': False, 'error': f'Invalid setting key: {key}'}), 400
            
            # Validate boolean settings
            if key in ['idle_intervention_enabled', 'progress_check_enabled']:
                if not isinstance(settings[key], bool):
                    return jsonify({'success': False, 'error': f'Setting value must be boolean: {key}'}), 400
            
            # Validate timing settings
            elif key == 'idle_intervention_delay':
                if not isinstance(settings[key], (int, float)) or not (1 <= settings[key] <= 60):
                    return jsonify({'success': False, 'error': f'Idle intervention delay must be between 1 and 60 seconds: {key}'}), 400
            
            elif key == 'progress_check_interval':
                if not isinstance(settings[key], (int, float)) or not (10 <= settings[key] <= 300):
                    return jsonify({'success': False, 'error': f'Progress check interval must be between 10 and 300 seconds: {key}'}), 400
        
        # Update settings
        ai_agent.intervention_service.update_intervention_settings(settings)
        
        return jsonify({
            'success': True,
            'message': 'Intervention settings updated successfully',
            'settings': ai_agent.intervention_service.get_intervention_settings()
        })
        
    except Exception as e:
        print(f"❌ Error updating intervention settings: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/code-executions/<room_id>', methods=['GET'])
def get_code_executions(room_id):
    """Get code execution history for a specific room"""
    try:
        # Get query parameters for pagination and filtering
        limit = request.args.get('limit', 50, type=int)
        skip = request.args.get('skip', 0, type=int)
        
        # Query code executions for the room, ordered by timestamp (newest first)
        executions = CodeExecution.objects(room_id=room_id).order_by('-timestamp').skip(skip).limit(limit)
        
        # Convert to dictionaries for JSON response
        execution_list = [execution.to_dict() for execution in executions]
        
        return jsonify({
            'success': True,
            'room_id': room_id,
            'executions': execution_list,
            'count': len(execution_list),
            'total': CodeExecution.objects(room_id=room_id).count()
        })
        
    except Exception as e:
        print(f"❌ Error retrieving code executions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == "__main__":
    try:
        socketio.run(app, host="0.0.0.0", port=5000, debug=False)
    finally:
        # Clean up database connection on shutdown
        close_db()
