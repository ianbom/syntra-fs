"""Celery application configuration with RabbitMQ broker."""
from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "syntra_worker",
    broker=settings.CELERY_BROKER_URL,
    include=["app.tasks.document_tasks"]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Jakarta",
    enable_utc=True,
    
    # Worker settings
    worker_concurrency=2,
    worker_prefetch_multiplier=1,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=600,          # 10 minutes max per task
    task_soft_time_limit=540,     # Soft limit at 9 minutes
)
