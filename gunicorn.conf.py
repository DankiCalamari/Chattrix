import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', 5000)}"
backlog = 2048

# Worker processes
workers = 1
worker_class = "eventlet"
worker_connections = 1000
timeout = 120
keepalive = 2

# Restart workers after this many requests, with up to this much jitter
max_requests = 1000
max_requests_jitter = 50

# Load application code before the worker processes are forked
preload_app = True

# Enable stdio inheritance
enable_stdio_inheritance = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "chattrix"

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Alternative configuration for environments where eventlet has issues
# Uncomment these lines and comment out the eventlet lines above if needed
# workers = multiprocessing.cpu_count() * 2 + 1
# worker_class = "gevent"
# worker_connections = 1000
