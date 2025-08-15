"""
Gunicorn configuration for Noctis DICOM Viewer
"""

import multiprocessing
import os

# Server socket
bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8000')
backlog = 2048

# Worker processes
workers = os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1)
worker_class = 'sync'
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# Timeout settings
timeout = 300  # 5 minutes for large DICOM uploads
keepalive = 2
graceful_timeout = 30

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'noctis-dicom-viewer'

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Performance
worker_tmp_dir = '/dev/shm'
max_requests = 1000
max_requests_jitter = 50

# SSL (if using HTTPS)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'

# Environment variables
raw_env = [
    'DJANGO_SETTINGS_MODULE=noctisview.production_settings',
]

# Pre-fork hooks
def on_starting(server):
    """Called just after the server is started."""
    server.log.info("Starting Noctis DICOM Viewer server")

def on_reload(server):
    """Called to reload the server."""
    server.log.info("Reloading Noctis DICOM Viewer server")

def worker_int(worker):
    """Called when a worker receives SIGINT or SIGQUIT."""
    worker.log.info("Worker received SIGINT or SIGQUIT")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    worker.log.info("Worker initialized (pid: %s)", worker.pid)

def worker_abort(worker):
    """Called when a worker is being aborted."""
    worker.log.info("Worker aborted (pid: %s)", worker.pid)

def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forked child, re-executing.")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Server is ready. Spawning workers")

def worker_exit(server, worker):
    """Called when a worker exits."""
    server.log.info("Worker exited (pid: %s)", worker.pid)

def on_exit(server):
    """Called just before exiting."""
    server.log.info("Server is shutting down")