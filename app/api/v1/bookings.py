from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.api.pagination import LimitParam, OffsetParam
from app.db.models import Booking, BookingStatus, SpecialistProfile, TimeSlot, User, UserRole
from app.db.session import get_db
from app.schemas.booking import BookingCreateRequest, BookingResponse
from app.services.calendar_service import build_booking_calendar_ics
from app.services.booking_service import create_booking_for_slot

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingCreateRequest,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    current_user: User = Depends(require_roles(UserRole.CLIENT, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> BookingResponse:
    normalized_idempotency_key: str | None = None
    if idempotency_key is not None:
        normalized_idempotency_key = idempotency_key.strip()
        if not normalized_idempotency_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Idempotency-Key header must not be empty",
            )
        if len(normalized_idempotency_key) > 128:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Idempotency-Key header is too long (max 128 characters)",
            )

    booking = create_booking_for_slot(
        db=db,
        slot_id=payload.slot_id,
        client_id=current_user.id,
        idempotency_key=normalized_idempotency_key,
    )
    return BookingResponse.model_validate(booking)


@router.patch("/{booking_id}/cancel", response_model=BookingResponse, status_code=status.HTTP_200_OK)
def cancel_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BookingResponse:
    booking = db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update())
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    slot = db.scalar(select(TimeSlot).where(TimeSlot.id == booking.slot_id).with_for_update())
    if not slot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slot not found")

    allowed = current_user.role == UserRole.ADMIN.value or booking.client_id == current_user.id
    if not allowed:
        specialist = db.scalar(
            select(SpecialistProfile).where(SpecialistProfile.id == slot.specialist_id)
        )
        if specialist and specialist.user_id == current_user.id:
            allowed = True
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    if booking.status != BookingStatus.CANCELLED.value:
        booking.cancel()
        slot.is_booked = False

    db.commit()
    db.refresh(booking)
    return BookingResponse.model_validate(booking)


@router.get("/{booking_id}/calendar.ics", status_code=status.HTTP_200_OK)
def download_booking_calendar_file(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    data = db.execute(
        select(Booking, TimeSlot, SpecialistProfile, User)
        .join(TimeSlot, Booking.slot_id == TimeSlot.id)
        .join(SpecialistProfile, TimeSlot.specialist_id == SpecialistProfile.id)
        .join(User, Booking.client_id == User.id)
        .where(Booking.id == booking_id)
    ).first()
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    booking, slot, specialist, client = data
    is_admin = current_user.role == UserRole.ADMIN.value
    is_client_owner = booking.client_id == current_user.id
    is_specialist_owner = specialist.user_id == current_user.id
    if not (is_admin or is_client_owner or is_specialist_owner):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    ics_content = build_booking_calendar_ics(
        booking_id=booking.id,
        slot_start_at=slot.start_at,
        slot_end_at=slot.end_at,
        specialist_display_name=specialist.display_name,
        client_email=client.email,
        booking_status=booking.status,
    )
    filename = f"booking-{booking.id}.ics"
    return Response(
        content=ics_content,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/me", response_model=list[BookingResponse], status_code=status.HTTP_200_OK)
def list_my_bookings(
    status_filter: BookingStatus | None = Query(default=None, alias="status"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: LimitParam = 20,
    offset: OffsetParam = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BookingResponse]:
    query = (
        select(Booking)
        .join(TimeSlot, Booking.slot_id == TimeSlot.id)
        .where(Booking.client_id == current_user.id)
    )
    if status_filter:
        query = query.where(Booking.status == status_filter.value)
    if date_from:
        start_dt = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        query = query.where(TimeSlot.start_at >= start_dt)
    if date_to:
        end_dt = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
        query = query.where(TimeSlot.start_at < end_dt)

    bookings = db.scalars(query.order_by(Booking.id).limit(limit).offset(offset)).all()
    return [BookingResponse.model_validate(booking) for booking in bookings]


@router.get("/specialists/me", response_model=list[BookingResponse], status_code=status.HTTP_200_OK)
def list_specialist_bookings(
    status_filter: BookingStatus | None = Query(default=None, alias="status"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: LimitParam = 20,
    offset: OffsetParam = 0,
    current_user: User = Depends(require_roles(UserRole.SPECIALIST, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> list[BookingResponse]:
    profile = db.scalar(select(SpecialistProfile).where(SpecialistProfile.user_id == current_user.id))
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specialist profile not found")

    query = (
        select(Booking)
        .join(TimeSlot, Booking.slot_id == TimeSlot.id)
        .where(TimeSlot.specialist_id == profile.id)
    )
    if status_filter:
        query = query.where(Booking.status == status_filter.value)
    if date_from:
        start_dt = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        query = query.where(TimeSlot.start_at >= start_dt)
    if date_to:
        end_dt = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
        query = query.where(TimeSlot.start_at < end_dt)

    bookings = db.scalars(query.order_by(Booking.id).limit(limit).offset(offset)).all()
    return [BookingResponse.model_validate(booking) for booking in bookings]
