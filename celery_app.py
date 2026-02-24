import os
from celery import Celery
from kombu import Exchange, Queue
from datetime import timedelta

# Initialize Celery app
app = Celery(
    'financial_analyzer',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/1'),
)

# Configure Celery
app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Broker settings
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    broker_heartbeat=30,
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={
        'db': 1,
        'password': os.getenv('REDIS_PASSWORD', ''),
        'connection_string': os.getenv('REDIS_URL', 'redis://localhost:6379/1'),
    },
    
    # Task routing
    task_routes={
        'tasks.analyze_financial_document_task': {'queue': 'analysis'},
        'tasks.verify_document_task': {'queue': 'verification'},
        'tasks.cleanup_old_files': {'queue': 'maintenance'},
    },
    
    # Queue definitions with routing
    task_queues=(
        Queue('analysis', Exchange('analysis'), routing_key='tasks.analyze_*'),
        Queue('verification', Exchange('verification'), routing_key='tasks.verify_*'),
        Queue('maintenance', Exchange('maintenance'), routing_key='tasks.cleanup_*'),
        Queue('default', Exchange('default'), routing_key='tasks.default'),
    ),
    
    # Scheduled tasks (if using Celery Beat)
    beat_schedule={
        'cleanup-old-files': {
            'task': 'tasks.cleanup_old_files',
            'schedule': timedelta(hours=24),  # Run daily
        },
    },
    
    # Task time limits
    task_soft_time_limit=600,  # 10 minutes soft limit
    task_time_limit=900,  # 15 minutes hard limit
    
    # Retry policy
    task_autoretry_for=(Exception,),
    task_max_retries=3,
    task_default_retry_delay=60,
)

# Configure logging for Celery
from celery.signals import task_prerun, task_postrun, task_failure
import logging

logger = logging.getLogger(__name__)


@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **extra):
    """Handler executed before task runs"""
    logger.info(f"Task {task.name} [{task_id}] starting")


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **extra):
    """Handler executed after task completes successfully"""
    logger.info(f"Task {task.name} [{task_id}] completed successfully")


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **extra):
    """Handler executed when task fails"""
    logger.error(f"Task {sender.name} [{task_id}] failed with exception: {exception}")


if __name__ == '__main__':
    app.start()
