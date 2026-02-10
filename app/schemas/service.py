from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ServiceCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    duration_minutes: int = Field(ge=5, le=480)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class ServiceResponse(BaseModel):
    id: int
    specialist_id: int
    title: str
    description: str | None
    duration_minutes: int
    price: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}
