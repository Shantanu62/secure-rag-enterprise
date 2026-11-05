import os
import secrets
from typing import Annotated
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.auth.dependencies import (
    get_current_user,
    require_permission,
)
from backend.auth.permissions import Role
from backend.auth.security import create_access_token
from backend.auth.user_service import authenticate_user, create_user
from backend.database.connection import get_db
from backend.core.config import settings
from backend.models.user import User
router = APIRouter(prefix="/auth", tags=["Authentication"])
class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)
class BootstrapAdminRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=12, max_length=128)
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
@router.post("/bootstrap-admin", status_code=status.HTTP_201_CREATED)
def bootstrap_admin(
    credentials: BootstrapAdminRequest,
    db: Annotated[Session, Depends(get_db)],
    bootstrap_token: Annotated[
        str | None,
        Header(alias="X-Bootstrap-Token"),
    ] = None,
):
    """Create the first Admin account using a one-time secret token."""
    configured_token = settings.ADMIN_BOOTSTRAP_TOKEN
    if not configured_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bootstrap is not enabled",
        )
    if (
        not bootstrap_token
        or not secrets.compare_digest(bootstrap_token, configured_token)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid bootstrap credentials",
        )
    if db.query(User).count() > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bootstrap is only available before the first user is created",
        )
    try:
        user = create_user(
            db=db,
            username=credentials.username,
            email=credentials.email,
            password=credentials.password,
            role=Role.ADMIN.value,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return {
        "message": "Initial Admin account created successfully",
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
    }
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

