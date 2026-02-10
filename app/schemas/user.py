from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.db.models.user import UserRole


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
