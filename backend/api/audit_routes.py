
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.auth.dependencies import require_permission
from backend.database.connection import get_db
from backend.models.audit_log import AuditLog


router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
)


class AuditLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    username: str
    action: str
    resource_type: str
    resource_id: str | None
    details: str | None
    ip_address: str | None
    created_at: datetime


class AuditLogPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[AuditLogItem]


@router.get("", response_model=AuditLogPage)
def list_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        dict,
        Depends(require_permission("audit:read")),
    ],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    action: Annotated[
        str | None,
        Query(min_length=1, max_length=100),
    ] = None,
    resource_type: Annotated[
        str | None,
        Query(min_length=1, max_length=100),
    ] = None,
):
    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action == action)

    if resource_type:
        query = query.filter(
            AuditLog.resource_type == resource_type
        )

    total = (
        query.with_entities(func.count(AuditLog.id)).scalar()
        or 0
    )

    entries = (
        query
        .order_by(
            AuditLog.created_at.desc(),
            AuditLog.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    return AuditLogPage(
        total=total,
        limit=limit,
        offset=offset,
        items=entries,
    )
