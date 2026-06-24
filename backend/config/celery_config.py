"""Celery configuration."""
import os

# Broker + Backend
broker_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
result_backend = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Serialization
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True

# Task settings
task_track_started = True
task_acks_late = True
worker_prefetch_multiplier = 1  # important pour les tâches longues

# Retry settings
task_max_retries = 3
task_default_retry_delay = 60  # seconds

task_time_limit = 1800      # 30 min
task_soft_time_limit = 1500

# Batch size
INGESTION_BATCH_SIZE = 50