"""gunicorn config for laopodada-api

Log paths default to ./logs relative to the project. Override via env var
so the same config works in CI (where /opt may be unwritable) and prod.
"""
import os

_log_dir = os.environ.get("LAOPODADA_LOG_DIR", "logs")
os.makedirs(_log_dir, exist_ok=True)

bind = "127.0.0.1:8097"
workers = int(os.environ.get("GUNICORN_WORKERS", "2"))
threads = 4
worker_class = "gthread"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
accesslog = os.path.join(_log_dir, "access.log")
errorlog  = os.path.join(_log_dir, "error.log")
loglevel = "info"
proc_name = "laopodada-api"
