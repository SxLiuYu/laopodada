"""gunicorn config for laopodada-api"""
bind = "127.0.0.1:8097"
workers = 2
threads = 4
worker_class = "gthread"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
accesslog = "/opt/laopodada-api/access.log"
errorlog = "/opt/laopodada-api/error.log"
loglevel = "info"
proc_name = "laopodada-api"
