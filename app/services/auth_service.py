from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.models.user import User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


def register_user(payload: RegisterRequest, db: Session) -> User:
    email = payload.email.lower()
    existing_user = db.scalar(select(User).where(User.email == email))
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    user = User(
        email=email,
        hashed_password=get_password_hash(payload.password),
        role=payload.role.value if isinstance(payload.role, UserRole) else payload.role,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        ) from None
    db.refresh(user)
    return user


def login_user(payload: LoginRequest, db: Session) -> TokenResponse:
    email = payload.email.lower()
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(subject=str(user.id), extra_claims={"role": user.role, "email": user.email})
    return TokenResponse(access_token=token)
