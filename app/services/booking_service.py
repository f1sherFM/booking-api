from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Booking, BookingStatus, TimeSlot


def create_booking_for_slot(db: Session, slot_id: int, client_id: int) -> Booking:
    slot_exists = db.scalar(select(TimeSlot.id).where(TimeSlot.id == slot_id))
    if not slot_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slot not found")

    try:
        updated = db.execute(
            update(TimeSlot)
            .where(TimeSlot.id == slot_id, TimeSlot.is_booked.is_(False))
            .values(is_booked=True)
        )
        if updated.rowcount != 1:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slot already booked")

        booking = Booking(
            slot_id=slot_id,
            client_id=client_id,
            status=BookingStatus.CONFIRMED.value,
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        return booking
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slot already booked") from None
