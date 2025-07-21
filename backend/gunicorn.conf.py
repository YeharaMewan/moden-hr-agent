# Gunicorn configuration for production
bind = "0.0.0.0:5000"
workers = 1  # For 512MB RAM limit on free tier
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2
preload_app = True