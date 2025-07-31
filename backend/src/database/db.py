
"""
Database configuration and connection setup
"""

import os
from mongoengine import connect, disconnect
from dotenv import load_dotenv

load_dotenv()


def init_db():
    """Initialize MongoDB connection"""
    try:
        mongodb_uri = os.environ.get('MONGODB_URI')
        
        # Disconnect any existing connections
        disconnect()
        
        # Connect to MongoDB
        connect(host=mongodb_uri)
        print(f"✅ Connected to MongoDB: {mongodb_uri}")
        
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        raise


def close_db():
    """Close MongoDB connection"""
    try:
        disconnect()
        print("✅ MongoDB connection closed")
    except Exception as e:
        print(f"❌ Error closing MongoDB connection: {e}")