
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.auth.permissions import has_permission
from backend.auth.security import decode_access_token
from backend.database.connection import get_db
from backend.models.user import User


bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials,
        Depends(bearer_scheme),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Validate JWT and retrieve the active user from the database."""

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        subject = payload.get("sub")

        if not subject:
            raise credentials_exception

        user_id = int(subject)
        user = db.query(User).filter(User.id == user_id).first()

        if not user or not user.is_active:
            raise credentials_exception

        return {
            "user_id": str(user.id),
            "username": user.username,
            "role": user.role,
            "department": user.department,
        }

    except (jwt.InvalidTokenError, ValueError):
        raise credentials_exception


def require_permission(permission: str):
    """Create a dependency that enforces a specific permission."""

    def permission_checker(
        current_user: Annotated[dict, Depends(get_current_user)],
    ) -> dict:
        if not has_permission(current_user["role"], permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )

        return current_user

    return permission_checker
