"""
app.py - Backend for remote pair programming
"""

import os
import subprocess
import threading
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

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
