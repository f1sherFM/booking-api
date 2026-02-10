from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class SlotCreateRequest(BaseModel):
    start_at: datetime
    end_at: datetime

    @model_validator(mode="after")
    def validate_interval(self) -> "SlotCreateRequest":
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be greater than start_at")
        return self


class SlotResponse(BaseModel):
    id: int
    specialist_id: int
    start_at: datetime
    end_at: datetime
    is_booked: bool

    model_config = {"from_attributes": True}


class SpecialistProfileResponse(BaseModel):
    id: int
    user_id: int
    display_name: str
    description: str | None

    model_config = {"from_attributes": True}
