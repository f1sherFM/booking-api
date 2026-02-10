from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.db.models import Booking, BookingStatus, TimeSlot


LOCK_CONFLICT_DETAIL = "Slot booking is in progress. Retry the request."
SLOT_ALREADY_BOOKED_DETAIL = "Slot already booked"
IDEMPOTENCY_KEY_REUSE_DETAIL = "Idempotency key already used with another slot"
PG_LOCK_NOT_AVAILABLE_SQLSTATE = "55P03"


def _is_postgresql_session(db: Session) -> bool:
    bind = db.get_bind()
    return bind is not None and bind.dialect.name == "postgresql"


def _is_pg_lock_not_available(exc: OperationalError) -> bool:
    original_error = getattr(exc, "orig", None)
    if original_error is None:
        return False

    sqlstate = getattr(original_error, "sqlstate", None)
    if sqlstate is None:
        sqlstate = getattr(original_error, "pgcode", None)

    return sqlstate == PG_LOCK_NOT_AVAILABLE_SQLSTATE


def _get_booking_by_idempotency_key(db: Session, client_id: int, idempotency_key: str) -> Booking | None:
    return db.scalar(
        select(Booking).where(
            Booking.client_id == client_id,
            Booking.idempotency_key == idempotency_key,
        )
    )


def create_booking_for_slot(
    db: Session,
    slot_id: int,
    client_id: int,
    idempotency_key: str | None = None,
) -> Booking:
    try:
        if idempotency_key:
            existing_booking = _get_booking_by_idempotency_key(
                db=db,
                client_id=client_id,
                idempotency_key=idempotency_key,
            )
            if existing_booking:
                if existing_booking.slot_id != slot_id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=IDEMPOTENCY_KEY_REUSE_DETAIL,
                    )
                return existing_booking

        slot_query = select(TimeSlot.id).where(TimeSlot.id == slot_id)
        if _is_postgresql_session(db):
            slot_query = slot_query.with_for_update(nowait=True)

        slot_exists = db.scalar(slot_query)
        if not slot_exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slot not found")

        updated = db.execute(
            update(TimeSlot)
            .where(TimeSlot.id == slot_id, TimeSlot.is_booked.is_(False))
            .values(is_booked=True)
        )
        if updated.rowcount != 1:
            db.rollback()
            if idempotency_key:
                existing_booking = _get_booking_by_idempotency_key(
                    db=db,
                    client_id=client_id,
                    idempotency_key=idempotency_key,
                )
                if existing_booking:
                    if existing_booking.slot_id != slot_id:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=IDEMPOTENCY_KEY_REUSE_DETAIL,
                        )
                    return existing_booking
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=SLOT_ALREADY_BOOKED_DETAIL)

        booking = Booking(
            slot_id=slot_id,
            client_id=client_id,
            idempotency_key=idempotency_key,
            status=BookingStatus.CONFIRMED.value,
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        return booking
    except OperationalError as exc:
        db.rollback()
        if _is_pg_lock_not_available(exc):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=LOCK_CONFLICT_DETAIL) from None
        raise
    except IntegrityError:
        db.rollback()
        if idempotency_key:
            existing_booking = _get_booking_by_idempotency_key(
                db=db,
                client_id=client_id,
                idempotency_key=idempotency_key,
            )
            if existing_booking:
                if existing_booking.slot_id != slot_id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=IDEMPOTENCY_KEY_REUSE_DETAIL,
                    ) from None
                return existing_booking
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=SLOT_ALREADY_BOOKED_DETAIL) from None
