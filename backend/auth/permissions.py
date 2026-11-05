
from enum import Enum


class Role(str, Enum):
    ADMIN = "Admin"
    MANAGER = "Manager"
    EMPLOYEE = "Employee"


ROLE_PERMISSIONS = {
    Role.ADMIN: {
        "document:read",
        "document:upload",
        "document:delete",
        "document:manage",
        "user:read",
        "user:manage",
        "audit:read",
    },
    Role.MANAGER: {
        "document:read",
        "document:upload",
        "document:manage",
        "user:read",
        "audit:read",
    },
    Role.EMPLOYEE: {
        "document:read",
    },
}


def has_permission(role: str, permission: str) -> bool:
    """Check whether a role has a specific permission."""
    try:
        normalized_role = Role(role)
    except ValueError:
        return False

    return permission in ROLE_PERMISSIONS.get(normalized_role, set())


def get_role_permissions(role: str) -> set[str]:
    """Return all permissions assigned to a role."""
    try:
        normalized_role = Role(role)
    except ValueError:
        return set()

    return ROLE_PERMISSIONS.get(normalized_role, set()).copy()
