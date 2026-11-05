
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.auth.dependencies import (
    get_current_user,
    require_permission,
)
from backend.auth.security import create_access_token
from backend.auth.user_service import authenticate_user
from backend.database.connection import get_db


router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
def login(
    credentials: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Authenticate a database user and issue a JWT access token."""
    user = authenticate_user(
        db=db,
        username=credentials.username,
        password=credentials.password,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_access_token(
        subject=str(user.id),
        role=user.role,
    )

    return TokenResponse(access_token=token)


@router.get("/me")
def get_me(
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Return the authenticated user's information."""
    return current_user


@router.get("/admin")
def admin_dashboard(
    current_user: Annotated[
        dict,
        Depends(require_permission("user:manage")),
    ],
):
    """Admin-only endpoint."""
    return {
        "message": "Admin access granted",
        "user": current_user,
    }
