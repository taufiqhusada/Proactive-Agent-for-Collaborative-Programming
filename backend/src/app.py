"""
app.py - Backend for remote pair programming
"""

import os
import subprocess
import threading
import time
import asyncio
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from services.ai_agent import init_ai_agent, get_ai_agent

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET", "change-me")
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET", "change-me-too")
CORS(app, supports_credentials=True)
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
    async_mode='threading'
)
jwt = JWTManager(app)

class ConnectionManager:
    """Track who's in which Socket.IO room and store room state."""
    def __init__(self):
        self.rooms = {}      # room_id -> set(sid)
        self.room_state = {} # room_id -> { code: str, language: str }

    def join(self, sid: str, room: str):
        self.rooms.setdefault(room, set()).add(sid)

    def leave(self, sid: str, room: str):
        self.rooms.get(room, set()).discard(sid)
        if room in self.rooms and not self.rooms[room]:
            self.rooms.pop(room, None)
            self.room_state.pop(room, None)

    def get_room_state(self, room: str):
        return self.room_state.get(room, {"code": 'print("Hello")', "language": "python"})

    def set_room_state(self, room: str, code: str, language: str = "python"):
        self.room_state[room] = {"code": code, "language": language}

manager = ConnectionManager()

# Initialize AI Agent
ai_agent = init_ai_agent(socketio)

# WebSocket handlers
@socketio.on("connect", namespace="/ws")
def ws_connect():
    print(f"WS client {request.sid} connected")

@socketio.on("join", namespace="/ws")
def ws_join(data):
    room = data["room"]
    join_room(room)
    manager.join(request.sid, room)
    
    # Get current room state and send to new user
    room_state = manager.get_room_state(room)
    current_user_count = len(manager.rooms.get(room, set()))
    print(f"Client {request.sid} joined room {room}, sending state. Users in room: {current_user_count}")
    
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
        "username": f"User {request.sid[-4:]}",
        "userCount": current_user_count
    }, room=room, include_self=False)
    
    return {"code": room_state["code"]}

@socketio.on("leave", namespace="/ws") 
def ws_leave(data):
    room = data["room"]
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
        "username": f"User {request.sid[-4:]}",
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
    
    # Broadcast chat message to all other clients in the room
    emit("chat_message", data, room=room, include_self=False)
    
    # Process message with AI agent in a separate thread
    def process_ai_message():
        ai_agent.process_message_sync(data)
    
    threading.Thread(target=process_ai_message, daemon=True).start()

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
    Handle voice activity detection from frontend to cancel pending 5-second timers.
    This provides much faster timer cancellation than waiting for completed messages.
    """
    room = data["room"]
    user_id = data["userId"]
    event_type = data["event"]  # 'speechstart' or 'speechend'
    timestamp = data["timestamp"]
    
    print(f"🎤 Voice activity detected: {event_type} from user {user_id} in room {room}")
    
    # Only cancel timers on speech start (when user begins speaking)
    if event_type == 'speechstart':
        print(f"🚫 Cancelling pending 5-second timers due to voice activity in room {room}")
        
        # Cancel any pending intervention timers immediately
        if room in ai_agent.conversation_history:
            context = ai_agent.conversation_history[room]
            if room in ai_agent.pending_timers:
                ai_agent._cancel_pending_intervention(room, "voice activity detected")
                print(f"✅ Successfully cancelled pending timer due to voice activity in room {room}")
            else:
                print(f"🔍 No pending timer to cancel in room {room}")
        else:
            print(f"⚠️ No conversation context found for room {room}")

@socketio.on("chat_typing_activity", namespace="/ws")
def ws_chat_typing_activity(data):
    """
    Handle chat typing activity detection from frontend to cancel pending 5-second timers.
    This provides immediate timer cancellation when users start typing in chat input.
    """
    room = data["room"]
    user_id = data["userId"]
    event_type = data["event"]  # 'typing_start'
    timestamp = data["timestamp"]
    
    print(f"⌨️  Chat typing activity detected: {event_type} from user {user_id} in room {room}")
    
    # Only cancel timers when user starts typing (active engagement)
    if event_type == 'typing_start':
        print(f"🚫 Cancelling pending 5-second timers due to chat typing activity in room {room}")
        
        # Cancel any pending intervention timers immediately
        if room in ai_agent.conversation_history:
            context = ai_agent.conversation_history[room]
            if room in ai_agent.pending_timers:
                ai_agent._cancel_pending_intervention(room, "chat typing activity detected")
                print(f"✅ Successfully cancelled pending timer due to chat typing in room {room}")
            else:
                print(f"🔍 No pending timer to cancel in room {room}")
        else:
            print(f"⚠️ No conversation context found for room {room}")

@socketio.on("disconnect", namespace="/ws")
def ws_disconnect():
    print(f"WS client {request.sid} disconnected")
    # Notify other users when someone disconnects
    for room in list(manager.rooms.keys()):
        if request.sid in manager.rooms.get(room, set()):
            manager.leave(request.sid, room)
            current_user_count = len(manager.rooms.get(room, set()))
            
            # Notify remaining users about updated count and disconnection
            emit("user_count_update", {
                "userCount": current_user_count
            }, room=room, include_self=False)
            
            emit("user_disconnected", {
                "userId": request.sid,
                "userCount": current_user_count
            }, room=room, include_self=False)


# REST API
@app.route("/", methods=["GET"])
def root():
    return "Hello, Remote Pair Programming!"

@app.route("/api/login", methods=["POST"])
def login():
    """
    Accept JSON {"username": ..., "password": ...}
    Returns {"access_token": "..."} for JWT-secured routes.
    """
    user = request.json.get("username", "guest")
    access = create_access_token(identity=user)
    return jsonify(access_token=access)

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
        
        # Trigger async AI validation if room_id provided (non-blocking)
        if room_id and ai_agent:
            try:
                ai_agent.start_execution_validation_optimized(room_id, code, result)
                print(f"🤖 Started async AI validation for room {room_id}")
            except Exception as validation_error:
                print(f"⚠️  AI validation error (non-blocking): {validation_error}")
        
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
                timeout=10,
                cwd=tempfile.gettempdir()
            )
            
        elif language == 'java':
            # Execute Java code (simplified - single class)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.java', delete=False) as f:
                # Simple wrapper for Java code
                if 'public class' not in code:
                    java_code = f'''
public class TempClass {{
    public static void main(String[] args) {{
        {code}
    }}
}}'''
                else:
                    java_code = code
                
                f.write(java_code)
                java_file = f.name
            
            try:
                # Compile Java
                compile_proc = subprocess.run(
                    ["javac", java_file],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=tempfile.gettempdir()
                )
                
                if compile_proc.returncode != 0:
                    return {
                        'output': '',
                        'error': f'Compilation error: {compile_proc.stderr}',
                        'exitCode': compile_proc.returncode,
                        'executionTime': (time.time() - start_time) * 1000
                    }
                
                # Run Java
                class_name = os.path.splitext(os.path.basename(java_file))[0]
                proc = subprocess.run(
                    ["java", "-cp", tempfile.gettempdir(), class_name],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=tempfile.gettempdir()
                )
                
            finally:
                # Clean up
                try:
                    os.unlink(java_file)
                    os.unlink(java_file.replace('.java', '.class'))
                except:
                    pass
                    
        elif language == 'cpp':
            # Execute C++ code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
                f.write(code)
                cpp_file = f.name
            
            try:
                # Compile C++
                exe_file = cpp_file.replace('.cpp', '.exe')
                compile_proc = subprocess.run(
                    ["g++", cpp_file, "-o", exe_file],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=tempfile.gettempdir()
                )
                
                if compile_proc.returncode != 0:
                    return {
                        'output': '',
                        'error': f'Compilation error: {compile_proc.stderr}',
                        'exitCode': compile_proc.returncode,
                        'executionTime': (time.time() - start_time) * 1000
                    }
                
                # Run C++
                proc = subprocess.run(
                    [exe_file],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=tempfile.gettempdir()
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

        print(f"📊 Code Analysis Request:")
        print(f"  Code: {code[:100]}...")
        print(f"  Language: {language}")
        print(f"  Context: {context}")
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
        return jsonify(result)
        
    except Exception as e:
        print(f"Error analyzing code block: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
