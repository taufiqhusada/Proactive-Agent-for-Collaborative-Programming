"""
app.py - Backend for remote pair programming
"""

import os
import subprocess
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_jwt_extended import JWTManager, create_access_token, jwt_required

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET", "change-me")
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET", "change-me-too")
CORS(app, supports_credentials=True)
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True,
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

@socketio.on("chat_message", namespace="/ws")
def ws_chat_message(data):
    """
    Forward chat messages to everyone else in the room.
    """
    print(f"WS chat message from {request.sid} in room {data['room']}")
    room = data["room"]
    
    # Broadcast chat message to all other clients in the room
    emit("chat_message", data, room=room, include_self=False)

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
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
