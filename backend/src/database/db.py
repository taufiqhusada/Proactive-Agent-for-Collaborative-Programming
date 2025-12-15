
"""
Database configuration and connection setup
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Global flag to track if MongoDB is available
_mongodb_enabled = False


def is_mongodb_enabled():
    """Check if MongoDB is enabled and connected"""
    return _mongodb_enabled


def init_db():
    """Initialize MongoDB connection if URI is provided"""
    global _mongodb_enabled
    
    try:
        mongodb_uri = os.environ.get('MONGODB_URI')
        
        if not mongodb_uri:
            print("ℹ️  MongoDB URI not provided - running without database (data tracking disabled)")
            _mongodb_enabled = False
            return
        
        # Try to import mongoengine (only needed if MongoDB is configured)
        try:
            from mongoengine import connect, disconnect
        except ImportError:
            print("⚠️  mongoengine not installed - running without database (data tracking disabled)")
            print("   Install with: pip install mongoengine")
            _mongodb_enabled = False
            return
        
        # Disconnect any existing connections
        disconnect()
        
        # Connect to MongoDB
        connect(host=mongodb_uri)
        _mongodb_enabled = True
        print(f"✅ Connected to MongoDB - data tracking enabled")
        
    except Exception as e:
        print(f"⚠️  Failed to connect to MongoDB: {e}")
        print("ℹ️  Continuing without database - data tracking disabled")
        _mongodb_enabled = False


def close_db():
    """Close MongoDB connection"""
    global _mongodb_enabled
    
    if not _mongodb_enabled:
        return
        
    try:
        from mongoengine import disconnect
        disconnect()
        _mongodb_enabled = False
        print("✅ MongoDB connection closed")
    except Exception as e:
        print(f"❌ Error closing MongoDB connection: {e}")