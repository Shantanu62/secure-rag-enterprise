
from sqlalchemy.orm import Session

from backend.models.audit_log import AuditLog


def record_audit_event(
    db: Session,
    current_user: dict,
    action: str,
    resource_type: str,
    resource_id: int | str | None = None,
    details: str | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """
    Add an audit event to the current database transaction.

    The caller is responsible for committing or rolling back
    the transaction. This keeps the business operation and its
    audit record atomic.
    """

    user_id = current_user.get("user_id")

    try:
        normalized_user_id = int(user_id) if user_id is not None else None
    except (TypeError, ValueError):
        normalized_user_id = None

    audit_entry = AuditLog(
        user_id=normalized_user_id,
        username=str(current_user.get("username", "unknown"))[:100],
        action=action[:100],
        resource_type=resource_type[:100],
        resource_id=(
            str(resource_id)[:100]
            if resource_id is not None
            else None
        ),
        details=details,
        ip_address=ip_address,
    )

    db.add(audit_entry)

    return audit_entry
