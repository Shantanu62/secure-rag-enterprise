from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from backend.auth.permissions import Role
from backend.models.document import Document
def _role_access_condition(role: str):
    """Match an exact role in comma-separated allowed_roles metadata."""
    return or_(
        Document.allowed_roles == role,
        Document.allowed_roles.like(f"{role},%"),
        Document.allowed_roles.like(f"%,{role},%"),
        Document.allowed_roles.like(f"%,{role}"),
    )
def _get_user_access_policy(current_user: dict):
    """Validate the user's role and return the access policy."""
    role = str(current_user.get("role", "")).strip()
    department = str(current_user.get("department", "")).strip()
    try:
        normalized_role = Role(role)
    except ValueError:
        return None, None
    return normalized_role.value, department
def get_accessible_documents(
    db: Session,
    current_user: dict,
) -> list[Document]:
    """Return active documents authorized for the current user."""
    role, department = _get_user_access_policy(current_user)
    if role is None:
        return []
    query = db.query(Document).filter(
        Document.is_active.is_(True)
    )
    if role == Role.ADMIN.value:
        return query.order_by(Document.created_at.desc()).all()
    access_condition = and_(
        Document.department == department,
        _role_access_condition(role),
    )
    return (
        query
        .filter(access_condition)
        .order_by(Document.created_at.desc())
        .all()
    )
def can_access_document(
    db: Session,
    current_user: dict,
    document_id: int,
) -> bool:
    """Check document access using strict department and role restrictions."""
    role, department = _get_user_access_policy(current_user)
    if role is None:
        return False
    query = db.query(Document).filter(
        Document.id == document_id,
        Document.is_active.is_(True),
    )
    if role == Role.ADMIN.value:
        return query.first() is not None
    access_condition = and_(
        Document.department == department,
        _role_access_condition(role),
    )
    return query.filter(access_condition).first() is not None
