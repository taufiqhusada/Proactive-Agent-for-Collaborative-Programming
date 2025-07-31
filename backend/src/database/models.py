"""
Database models for the HHAI Pair Programming application
"""

from mongoengine import Document, StringField, DateTimeField, IntField
from datetime import datetime


class CodeExecution(Document):
    """Model for storing code execution history"""
    
    room_id = StringField(required=True, max_length=200)
    code = StringField(required=True)
    language = StringField(required=True, default='python', max_length=50)
    timestamp = DateTimeField(required=True, default=datetime.utcnow)
    execution_output = StringField()
    execution_error = StringField()
    execution_time_ms = IntField()
    
    meta = {
        'collection': 'code_executions',
        'indexes': [
            'room_id',
            'timestamp',
            ('room_id', 'timestamp')
        ]
    }
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'room_id': self.room_id,
            'code': self.code,
            'language': self.language,
            'timestamp': self.timestamp.isoformat(),
            'execution_output': self.execution_output,
            'execution_error': self.execution_error,
            'execution_time_ms': self.execution_time_ms
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