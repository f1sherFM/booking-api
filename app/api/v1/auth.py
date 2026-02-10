from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limiter import rate_limiter
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services.auth_service import login_user, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _rate_limit_or_raise(endpoint: str, request: Request, response: Response) -> None:
    client_ip = request.client.host if request.client else "unknown"
    key = f"{endpoint}:{client_ip}"
    if endpoint == "register":
        limit = settings.auth_register_max_attempts
    else:
        limit = settings.auth_login_max_attempts

    allowed, retry_after = rate_limiter.allow(
        key=key,
        limit=limit,
        window_seconds=settings.auth_rate_limit_window_seconds,
    )
    if not allowed:
        response.headers["Retry-After"] = str(retry_after)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> UserResponse:
    _rate_limit_or_raise(endpoint="register", request=request, response=response)
    user = register_user(payload=payload, db=db)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    _rate_limit_or_raise(endpoint="login", request=request, response=response)
    return login_user(payload=payload, db=db)
