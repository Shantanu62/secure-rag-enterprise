
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.main import app
from backend.auth.dependencies import get_current_user
from backend.database.connection import Base, get_db
from backend.models.user import User
from backend.models.audit_log import AuditLog
from backend.auth.security import hash_password


@pytest.fixture
def audit_environment():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    admin = User(
        username="audit_admin",
        email="audit_admin@example.test",
        hashed_password=hash_password("TestPassword123!"),
        role="Admin",
        department="General",
        is_active=True,
    )

    manager = User(
        username="audit_manager",
        email="audit_manager@example.test",
        hashed_password=hash_password("TestPassword123!"),
        role="Manager",
        department="Engineering",
        is_active=True,
    )

    employee = User(
        username="audit_employee",
        email="audit_employee@example.test",
        hashed_password=hash_password("TestPassword123!"),
        role="Employee",
        department="Engineering",
        is_active=True,
    )

    db.add_all([admin, manager, employee])
    db.commit()

    audit_entries = [
        AuditLog(
            user_id=admin.id,
            username=admin.username,
            action="DOCUMENT_UPLOAD",
            resource_type="Document",
            resource_id="101",
            details="Document uploaded successfully",
            ip_address="127.0.0.1",
        ),
        AuditLog(
            user_id=manager.id,
            username=manager.username,
            action="DOCUMENT_DELETE",
            resource_type="Document",
            resource_id="102",
            details="Document soft-deleted successfully",
            ip_address="127.0.0.1",
        ),
        AuditLog(
            user_id=admin.id,
            username=admin.username,
            action="USER_LOGIN",
            resource_type="User",
            resource_id=str(admin.id),
            details="User login successful",
            ip_address="127.0.0.1",
        ),
    ]

    db.add_all(audit_entries)
    db.commit()

    current_user = {
        "user_id": str(admin.id),
        "username": admin.username,
        "role": admin.role,
        "department": admin.department,
    }

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user

    client = TestClient(app)

    yield {
        "client": client,
        "db": db,
        "admin": admin,
        "manager": manager,
        "employee": employee,
        "current_user": current_user,
    }

    client.close()
    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_admin_can_read_audit_logs(audit_environment):
    response = audit_environment["client"].get("/audit-logs")

    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert len(response.json()["items"]) == 3


def test_manager_can_read_audit_logs(audit_environment):
    manager = audit_environment["manager"]

    audit_environment["current_user"].update({
        "user_id": str(manager.id),
        "username": manager.username,
        "role": manager.role,
        "department": manager.department,
    })

    response = audit_environment["client"].get("/audit-logs")

    assert response.status_code == 200
    assert response.json()["total"] == 3


def test_employee_cannot_read_audit_logs(audit_environment):
    employee = audit_environment["employee"]

    audit_environment["current_user"].update({
        "user_id": str(employee.id),
        "username": employee.username,
        "role": employee.role,
        "department": employee.department,
    })

    response = audit_environment["client"].get("/audit-logs")

    assert response.status_code == 403


def test_audit_logs_support_pagination(audit_environment):
    response = audit_environment["client"].get(
        "/audit-logs",
        params={"limit": 2, "offset": 1},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 3
    assert data["limit"] == 2
    assert data["offset"] == 1
    assert len(data["items"]) == 2


def test_audit_logs_support_action_filter(audit_environment):
    response = audit_environment["client"].get(
        "/audit-logs",
        params={"action": "DOCUMENT_UPLOAD"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["action"] == "DOCUMENT_UPLOAD"


def test_audit_logs_support_resource_type_filter(audit_environment):
    response = audit_environment["client"].get(
        "/audit-logs",
        params={"resource_type": "User"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["resource_type"] == "User"


def test_audit_logs_reject_invalid_limit(audit_environment):
    response = audit_environment["client"].get(
        "/audit-logs",
        params={"limit": 101},
    )

    assert response.status_code == 422


def test_audit_logs_reject_negative_offset(audit_environment):
    response = audit_environment["client"].get(
        "/audit-logs",
        params={"offset": -1},
    )

    assert response.status_code == 422
