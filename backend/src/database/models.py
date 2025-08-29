"""
Database models for the HHAI Pair Programming application
"""

from mongoengine import Document, StringField, DateTimeField, IntField, BooleanField, ListField, DictField
from datetime import datetime


class ChatMessage(Document):
    """Model for storing chat messages in conversation history"""
    
    message_id = StringField(required=True, max_length=200)
    content = StringField(required=True)
    username = StringField(required=True, max_length=100)
    user_id = StringField(required=True, max_length=100)
    room_id = StringField(required=True, max_length=200)
    session_id = StringField(required=True, max_length=200)  # Programming session ID
    message_number = IntField(required=True)  # Sequential message number within session
    timestamp = DateTimeField(required=True, default=datetime.utcnow)
    is_auto_generated = BooleanField(default=False)
    
    # AI-specific metadata
    is_ai_message = BooleanField(default=False)
    ai_trigger_type = StringField(max_length=50)  # 'direct_mention', 'idle_5s', 'progress_check', etc.
    is_reflection = BooleanField(default=False)
    
    meta = {
        'collection': 'chat_messages',
        'indexes': [
            'room_id',
            'session_id',
            'timestamp',
            'user_id',
            'message_number',
            ('room_id', 'timestamp'),
            ('session_id', 'message_number'),
            ('room_id', 'user_id'),
            'is_ai_message'
        ]
    }
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'message_id': self.message_id,
            'content': self.content,
            'username': self.username,
            'user_id': self.user_id,
            'room_id': self.room_id,
            'session_id': self.session_id,
            'message_number': self.message_number,
            'timestamp': self.timestamp.isoformat(),
            'is_auto_generated': self.is_auto_generated,
            'is_ai_message': self.is_ai_message,
            'ai_trigger_type': self.ai_trigger_type,
            'is_reflection': self.is_reflection
        }
    
    def __str__(self):
        return f"ChatMessage(room_id={self.room_id}, username={self.username}, timestamp={self.timestamp})"


class CodeExecution(Document):
    """Model for storing code execution history"""
    
    room_id = StringField(required=True, max_length=200)
    session_id = StringField(max_length=200)  # Programming session ID
    code = StringField(required=True)
    language = StringField(required=True, default='python', max_length=50)
    timestamp = DateTimeField(required=True, default=datetime.utcnow)
    execution_output = StringField()
    execution_error = StringField()
    execution_time_ms = IntField()
    
    # Chat conversation context at time of execution
    chat_history = ListField(DictField(), default=list)  # Complete conversation history
    message_count = IntField(default=0)  # Total number of messages in chat_history
    
    meta = {
        'collection': 'code_executions',
        'indexes': [
            'room_id',
            'session_id',
            'timestamp',
            ('room_id', 'timestamp'),
            ('session_id', 'timestamp')
        ]
    }
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'room_id': self.room_id,
            'session_id': self.session_id,
            'code': self.code,
            'language': self.language,
            'timestamp': self.timestamp.isoformat(),
            'execution_output': self.execution_output,
            'execution_error': self.execution_error,
            'execution_time_ms': self.execution_time_ms,
            'chat_history': self.chat_history,
            'message_count': self.message_count
        }
    
    def __str__(self):
        return f"CodeExecution(room_id={self.room_id}, timestamp={self.timestamp})"


# Legacy model - keeping for backward compatibility
class InterviewTranscript(Document):
    """Legacy model for interview transcripts"""
    sessionID = StringField(required=True, unique=True)
    datetime = DateTimeField(default=datetime.utcnow)
    transcript = StringField()
    feedback = StringField()