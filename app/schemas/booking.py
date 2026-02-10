from datetime import datetime

from pydantic import BaseModel


class BookingCreateRequest(BaseModel):
    slot_id: int


class BookingRescheduleRequest(BaseModel):
    slot_id: int


class BookingResponse(BaseModel):
    id: int
    slot_id: int
    client_id: int
    status: str
    created_at: datetime
    cancelled_at: datetime | None

    model_config = {"from_attributes": True}


class SpecialistBookingSummaryResponse(BookingResponse):
    client_email: str
    slot_start_at: datetime
    slot_end_at: datetime
