import os
from dotenv import load_dotenv

load_dotenv()

# Gunicorn configuration for Cloud Run optimization
bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"

# Worker configuration for better performance
workers = 2  # 2 CPUs = 2 workers
worker_class = "eventlet"  # Async workers for Socket.IO
worker_connections = 100

# Performance tuning
max_requests = 1000
max_requests_jitter = 50
preload_app = True
timeout = 300
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'