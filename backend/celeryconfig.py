"""
Celery configuration for async task processing
"""
from celery import Celery
from config import Config

# Load configuration
config = Config.load()

# Create Celery app
celery_app = Celery('dbrag')

# Configure Celery
celery_app.conf.update(
    broker_url=config.celery.broker_url,
    result_backend=config.celery.result_backend,
    task_serializer=config.celery.task_serializer,
    result_serializer=config.celery.result_serializer,
    accept_content=config.celery.accept_content,
    timezone=config.celery.timezone,
    enable_utc=config.celery.enable_utc,
    task_acks_late=config.celery.task_acks_late,
    task_reject_on_worker_lost=config.celery.task_reject_on_worker_lost,
    
    # Task routing (priority queues)
    task_routes={
        'tasks.ingest_document_task': {'queue': 'default'},
        'tasks.update_table_metadata_task': {'queue': 'default'},
        'tasks.batch_update_metadata_task': {'queue': 'low'},
        'tasks.rebuild_vector_indexes_task': {'queue': 'low'},
    },
    
    # Worker settings
    worker_prefetch_multiplier=1,  # Don't prefetch tasks
    worker_max_tasks_per_child=100,  # Restart after 100 tasks
    
    # Result expiration
    result_expires=3600,  # 1 hour
    
    # Task time limits
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=600,  # 10 minutes hard limit
)

# Optional: Configure beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'rebuild-indexes-daily': {
        'task': 'tasks.rebuild_vector_indexes_task',
        'schedule': 86400.0,  # Every 24 hours
    },
}
