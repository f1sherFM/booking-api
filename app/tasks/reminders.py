from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Booking, BookingStatus, TimeSlot
from app.db.session import SessionLocal
from app.tasks.celery_app import celery_app


def count_upcoming_bookings_for_reminder(db: Session, now: datetime | None = None) -> int:
    current_time = now or datetime.now(UTC)
    reminder_until = current_time + timedelta(minutes=settings.reminder_lookahead_minutes)

    upcoming = db.scalars(
        select(Booking)
        .join(TimeSlot, Booking.slot_id == TimeSlot.id)
        .where(
            Booking.status == BookingStatus.CONFIRMED.value,
            TimeSlot.start_at >= current_time,
            TimeSlot.start_at < reminder_until,
        )
    ).all()
    return len(upcoming)


@celery_app.task(name="bookings.remind_upcoming")
def remind_upcoming_bookings_task() -> dict[str, int]:
    db = SessionLocal()
    try:
        reminder_count = count_upcoming_bookings_for_reminder(db=db)
        return {"to_remind": reminder_count}
    finally:
        db.close()
