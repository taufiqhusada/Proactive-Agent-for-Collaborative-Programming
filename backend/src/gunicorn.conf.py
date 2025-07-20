import os
from dotenv import load_dotenv

load_dotenv()

# Gunicorn configuration for Flask-SocketIO with eventlet
bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"

# Worker configuration for Socket.IO
workers = 1  # Socket.IO requires single worker with eventlet
worker_class = "eventlet"  # Required for Socket.IO WebSocket support
worker_connections = 100

# Performance tuning
max_requests = 1000
max_requests_jitter = 50
timeout = 300
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'