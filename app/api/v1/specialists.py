from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.api.pagination import LimitParam, OffsetParam
from app.db.models import Service, SpecialistProfile, TimeSlot, User, UserRole
from app.db.session import get_db
from app.schemas.slot import SlotCreateRequest, SlotResponse, SpecialistProfileResponse
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
