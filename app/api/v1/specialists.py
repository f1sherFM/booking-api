from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.api.pagination import LimitParam, OffsetParam
from app.db.models import Service, SpecialistProfile, TimeSlot, User, UserRole
from app.db.session import get_db
from app.schemas.slot import (
    SlotCreateRequest,
    SlotResponse,
    SpecialistAvailabilityDayResponse,
    SpecialistProfileResponse,
)
from app.schemas.service import ServiceCreateRequest, ServiceResponse

router = APIRouter(prefix="/specialists", tags=["specialists"])


def _get_or_create_specialist_profile(db: Session, user: User) -> SpecialistProfile:
    profile = db.scalar(select(SpecialistProfile).where(SpecialistProfile.user_id == user.id))
    if profile:
        return profile

    profile = SpecialistProfile(
        user_id=user.id,
        display_name=user.email.split("@")[0],
        description=None,
    )
    db.add(profile)
    db.flush()
    return profile


@router.post("/me/services", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
def create_service_for_me(
    payload: ServiceCreateRequest,
    current_user: User = Depends(require_roles(UserRole.SPECIALIST, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ServiceResponse:
    profile = _get_or_create_specialist_profile(db=db, user=current_user)
    service = Service(
        specialist_id=profile.id,
        title=payload.title,
        description=payload.description,
        duration_minutes=payload.duration_minutes,
        price=payload.price,
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return ServiceResponse.model_validate(service)


@router.get("/{specialist_id}/services", response_model=list[ServiceResponse], status_code=status.HTTP_200_OK)
def list_specialist_services(
    specialist_id: int,
    limit: LimitParam = 20,
    offset: OffsetParam = 0,
    db: Session = Depends(get_db),
) -> list[ServiceResponse]:
    specialist = db.scalar(select(SpecialistProfile).where(SpecialistProfile.id == specialist_id))
    if not specialist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specialist not found")

    services = db.scalars(
        select(Service).where(Service.specialist_id == specialist_id).order_by(Service.id).limit(limit).offset(offset)
    ).all()
    return [ServiceResponse.model_validate(service) for service in services]


@router.get("/me", status_code=status.HTTP_200_OK)
def get_my_specialist_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SpecialistProfileResponse:
    profile = db.scalar(select(SpecialistProfile).where(SpecialistProfile.user_id == current_user.id))
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specialist profile not found")
    return SpecialistProfileResponse.model_validate(profile)


@router.post("/me/slots", response_model=SlotResponse, status_code=status.HTTP_201_CREATED)
def create_slot_for_me(
    payload: SlotCreateRequest,
    current_user: User = Depends(require_roles(UserRole.SPECIALIST, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> SlotResponse:
    profile = _get_or_create_specialist_profile(db=db, user=current_user)

    overlap = db.scalar(
        select(TimeSlot).where(
            and_(
                TimeSlot.specialist_id == profile.id,
                TimeSlot.start_at < payload.end_at,
                TimeSlot.end_at > payload.start_at,
            )
        )
    )
    if overlap:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Time slot overlaps with existing slot")

    slot = TimeSlot(
        specialist_id=profile.id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        is_booked=False,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return SlotResponse.model_validate(slot)


@router.delete("/me/slots/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_slot_for_me(
    slot_id: int,
    current_user: User = Depends(require_roles(UserRole.SPECIALIST, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> Response:
    profile = db.scalar(select(SpecialistProfile).where(SpecialistProfile.user_id == current_user.id))
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specialist profile not found")

    slot = db.scalar(
        select(TimeSlot).where(
            TimeSlot.id == slot_id,
            TimeSlot.specialist_id == profile.id,
        )
    )
    if not slot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slot not found")

    if slot.is_booked:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booked slot cannot be deleted")

    db.delete(slot)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{specialist_id}/slots", response_model=list[SlotResponse], status_code=status.HTTP_200_OK)
def list_specialist_slots(
    specialist_id: int,
    date_filter: date | None = Query(default=None, alias="date"),
    limit: LimitParam = 20,
    offset: OffsetParam = 0,
    db: Session = Depends(get_db),
) -> list[SlotResponse]:
    specialist = db.scalar(select(SpecialistProfile).where(SpecialistProfile.id == specialist_id))
    if not specialist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specialist not found")

    query = select(TimeSlot).where(TimeSlot.specialist_id == specialist_id)
    if date_filter:
        start_of_day = datetime.combine(date_filter, time.min, tzinfo=timezone.utc)
        end_of_day = start_of_day + timedelta(days=1)
        query = query.where(TimeSlot.start_at >= start_of_day, TimeSlot.start_at < end_of_day)

    slots = db.scalars(query.order_by(TimeSlot.start_at).limit(limit).offset(offset)).all()
    return [SlotResponse.model_validate(slot) for slot in slots]


@router.get(
    "/{specialist_id}/availability",
    response_model=list[SpecialistAvailabilityDayResponse],
    status_code=status.HTTP_200_OK,
)
def get_specialist_availability(
    specialist_id: int,
    date_from: date | None = Query(default=None),
    days: int = Query(default=7, ge=1, le=31),
    db: Session = Depends(get_db),
) -> list[SpecialistAvailabilityDayResponse]:
    specialist = db.scalar(select(SpecialistProfile).where(SpecialistProfile.id == specialist_id))
    if not specialist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specialist not found")

    start_date = date_from or datetime.now(timezone.utc).date()
    start_of_window = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end_of_window = start_of_window + timedelta(days=days)

    slots = db.scalars(
        select(TimeSlot)
        .where(
            TimeSlot.specialist_id == specialist_id,
            TimeSlot.start_at >= start_of_window,
            TimeSlot.start_at < end_of_window,
        )
        .order_by(TimeSlot.start_at)
    ).all()

    stats: dict[date, dict[str, int]] = {
        start_date + timedelta(days=offset): {"total": 0, "free": 0, "booked": 0}
        for offset in range(days)
    }

    for slot in slots:
        slot_date = slot.start_at.astimezone(timezone.utc).date()
        day_stats = stats.get(slot_date)
        if day_stats is None:
            continue

        day_stats["total"] += 1
        if slot.is_booked:
            day_stats["booked"] += 1
        else:
            day_stats["free"] += 1

    return [
        SpecialistAvailabilityDayResponse(
            date=day,
            total_slots=day_stats["total"],
            free_slots=day_stats["free"],
            booked_slots=day_stats["booked"],
        )
        for day, day_stats in stats.items()
    ]
