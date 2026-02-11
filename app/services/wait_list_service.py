from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Booking, BookingStatus, TimeSlot, WaitListEntry
from app.services.booking_service import create_booking_for_slot

SLOT_IS_AVAILABLE_DETAIL = "Slot is available. Book directly"
ALREADY_IN_WAIT_LIST_DETAIL = "Client is already in wait list for this slot"
ALREADY_HAS_BOOKING_DETAIL = "Client already has booking for this slot"


def add_client_to_wait_list(db: Session, slot_id: int, client_id: int) -> WaitListEntry:
    slot = db.scalar(select(TimeSlot).where(TimeSlot.id == slot_id))
    if not slot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slot not found")

    if not slot.is_booked:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=SLOT_IS_AVAILABLE_DETAIL)

    existing_booking = db.scalar(
        select(Booking).where(
            Booking.slot_id == slot_id,
            Booking.client_id == client_id,
            Booking.status == BookingStatus.CONFIRMED.value,
        )
    )
    if existing_booking:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ALREADY_HAS_BOOKING_DETAIL)

    entry = WaitListEntry(slot_id=slot_id, client_id=client_id)
    db.add(entry)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ALREADY_IN_WAIT_LIST_DETAIL) from None

    db.refresh(entry)
    return entry


def promote_next_wait_list_entry(db: Session, slot_id: int) -> Booking | None:
    entry = db.scalar(
        select(WaitListEntry)
        .where(WaitListEntry.slot_id == slot_id)
        .order_by(WaitListEntry.created_at, WaitListEntry.id)
    )
    if not entry:
        return None

    promoted_booking = create_booking_for_slot(db=db, slot_id=slot_id, client_id=entry.client_id)

    db.delete(entry)
    db.commit()
    return promoted_booking
