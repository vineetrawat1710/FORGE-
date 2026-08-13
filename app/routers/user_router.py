from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.schemas.user import Token, UserCreate, UserLogin, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    service = UserService(db)
    return service.register(payload)


@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
def login_user(payload: UserLogin, db: Session = Depends(get_db)) -> Token:
    service = UserService(db)
    return service.login(payload)


@router.post("/refresh", response_model=Token, status_code=status.HTTP_200_OK)
def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> Token:
    service = UserService(db)
    return service.refresh(payload.refresh_token)


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    return current_user
