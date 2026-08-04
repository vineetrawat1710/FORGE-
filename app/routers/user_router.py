from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.schemas.user import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserResponse:
    service = UserService(db)
    return service.register(payload)


@router.post("/login", response_model=TokenResponse)
def login_user(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    service = UserService(db)
    return service.login(payload)


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    return current_user
