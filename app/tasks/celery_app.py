from datetime import timedelta
import os

from celery import Celery

from app.core.config import settings

broker_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

celery_app = Celery(
    "booking",
    broker=broker_url,
    backend=result_backend,
    include=["app.tasks.expirations", "app.tasks.reminders"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "expire-started-bookings": {
            "task": "bookings.expire_started_slots",
            "schedule": timedelta(minutes=settings.celery_expiration_interval_minutes),
        },
        "remind-upcoming-bookings": {
            "task": "bookings.remind_upcoming",
            "schedule": timedelta(minutes=settings.celery_reminder_interval_minutes),
        },
    },
)
