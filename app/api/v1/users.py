from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.api.pagination import LimitParam, OffsetParam
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.get("", response_model=list[UserResponse], status_code=status.HTTP_200_OK)
def list_users(
    _: User = Depends(require_roles(UserRole.ADMIN)),
    limit: LimitParam = 20,
    offset: OffsetParam = 0,
    db: Session = Depends(get_db),
) -> list[UserResponse]:
    users = db.scalars(select(User).order_by(User.id).limit(limit).offset(offset)).all()
    return [UserResponse.model_validate(user) for user in users]
