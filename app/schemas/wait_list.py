from datetime import datetime

from pydantic import BaseModel


class WaitListCreateRequest(BaseModel):
    slot_id: int


class WaitListEntryResponse(BaseModel):
    id: int
    slot_id: int
    client_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
