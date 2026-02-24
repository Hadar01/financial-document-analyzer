#!/usr/bin/env python
"""
Celery Worker Entry Point
Starts a Celery worker process to handle async analysis tasks
Usage: python worker.py
"""

import os
import logging
from celery import signals
from celery_app import app
import tasks  # Import tasks to register them

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@signals.worker_ready.connect
def worker_ready(**kwargs):
    """Called when the worker is ready to accept tasks"""
    logger.info("✓ Celery worker is ready and listening for tasks")


@signals.worker_shutdown.connect
def worker_shutdown(**kwargs):
    """Called when the worker is shutting down"""
    logger.info("Worker shutting down gracefully...")


@signals.task_prerun.connect
def task_prerun_handler(task_id=None, task=None, args=None, kwargs=None, **extra):
    """Called before each task execution"""
    logger.info(f"→ Starting task: {task.name} [ID: {task_id}]")


@signals.task_postrun.connect
def task_postrun_handler(task_id=None, task=None, retval=None, **extra):
    """Called after successful task completion"""
    logger.info(f"✓ Task completed: {task.name} [ID: {task_id}]")


@signals.task_failure.connect
def task_failure_handler(task_id=None, exception=None, args=None, traceback=None, **extra):
    """Called when a task fails"""
    logger.error(f"✗ Task failed: {task_id} with exception: {exception}")


def main():
    """Main worker entry point"""
    
    # Get configuration values
    log_level = os.getenv('CELERY_LOG_LEVEL', 'INFO')
    concurrency = os.getenv('CELERY_CONCURRENCY', '4')
    pool_type = os.getenv('CELERY_POOL', 'prefork')
    
    logger.info("=" * 60)
    logger.info("Financial Document Analyzer - Celery Worker")
    logger.info("=" * 60)
    logger.info(f"Broker: {os.getenv('REDIS_URL', 'redis://localhost:6379/0')}")
    logger.info(f"Backend: {os.getenv('REDIS_URL', 'redis://localhost:6379/1')}")
    logger.info(f"Concurrency: {concurrency}")
    logger.info(f"Log Level: {log_level}")
    logger.info(f"Pool Type: {pool_type}")
    logger.info("=" * 60)
    
    try:
        # Build command line arguments
        argv = [
            'worker',
            '--loglevel', log_level,
            '--concurrency', concurrency,
            '--pool', pool_type,
            '--prefetch-multiplier', '1',
            '--max-tasks-per-child', '1000',
            '--without-gossip',
            '--without-mingle',
        ]
        
        app.worker_main(argv=argv)
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker crashed: {str(e)}", exc_info=True)
        exit(1)


if __name__ == '__main__':
    main()
