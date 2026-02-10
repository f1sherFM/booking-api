from datetime import datetime

from pydantic import BaseModel


class BookingCreateRequest(BaseModel):
    slot_id: int


class BookingResponse(BaseModel):
    id: int
    slot_id: int
    client_id: int
    status: str
    created_at: datetime
    cancelled_at: datetime | None

    model_config = {"from_attributes": True}
