from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Booking, BookingStatus, TimeSlot
from app.db.session import SessionLocal
from app.tasks.celery_app import celery_app
from app.services.wait_list_service import promote_next_wait_list_entry


def expire_started_slots(db: Session, now: datetime | None = None) -> int:
    current_time = now or datetime.now(UTC)
    expire_before = current_time - timedelta(minutes=settings.booking_expire_after_start_minutes)

    stale_bookings = db.scalars(
        select(Booking)
        .join(TimeSlot, Booking.slot_id == TimeSlot.id)
        .where(
            Booking.status == BookingStatus.CONFIRMED.value,
            TimeSlot.start_at <= expire_before,
        )
    ).all()

    for booking in stale_bookings:
        booking.status = BookingStatus.EXPIRED.value
        booking.cancelled_at = current_time
        booking.slot.is_booked = False

    if stale_bookings:
        db.commit()

    for booking in stale_bookings:
        promote_next_wait_list_entry(db=db, slot_id=booking.slot_id)

    return len(stale_bookings)


@celery_app.task(name="bookings.expire_started_slots")
def expire_started_slots_task() -> dict[str, int]:
    db = SessionLocal()
    try:
        expired_count = expire_started_slots(db=db)
        return {"expired": expired_count}
    finally:
        db.close()
