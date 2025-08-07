# Gunicorn configuration file
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 300
graceful_timeout = 30
keepalive = 2

# Server mechanics
daemon = False
raw_env = []
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Logging
accesslog = "/app/logs/gunicorn-access.log"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
errorlog = "/app/logs/gunicorn-error.log"
loglevel = "info"
capture_output = True
enable_stdio_inheritance = True

# Process naming
proc_name = "noctis_gunicorn"

# Server hooks
def on_starting(server):
    server.log.info("Starting NOCTIS DICOM Viewer")

def on_reload(server):
    server.log.info("Reloading NOCTIS DICOM Viewer")

def pre_fork(server, worker):
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def post_fork(server, worker):
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def worker_int(worker):
    worker.log.info(f"Worker received INT or QUIT signal")

def pre_exec(server):
    server.log.info("Forked child, re-executing.")

def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_abort(worker):
    worker.log.info(f"Worker received SIGABRT signal")

# SSL support (if needed)
# keyfile = "/app/ssl/key.pem"
# certfile = "/app/ssl/cert.pem"
# ssl_version = ssl.PROTOCOL_TLSv1_2
# cert_reqs = ssl.CERT_NONE
# ca_certs = None
# ciphers = "TLSv1.2"