
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.main import app
from backend.api.document_routes import settings as upload_settings
from backend.auth.dependencies import get_current_user
from backend.database.connection import Base, get_db
from backend.models.user import User
from backend.models.document import Document
from backend.models.audit_log import AuditLog
from backend.auth.security import hash_password


@pytest.fixture
def test_environment(tmp_path, monkeypatch):
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
        username="test_admin",
        email="admin@example.test",
        hashed_password=hash_password("TestPassword123!"),
        role="Admin",
        department="Engineering",
        is_active=True,
    )

    manager = User(
        username="test_manager",
        email="manager@example.test",
        hashed_password=hash_password("TestPassword123!"),
        role="Manager",
        department="Engineering",
        is_active=True,
    )

    employee = User(
        username="test_employee",
        email="employee@example.test",
        hashed_password=hash_password("TestPassword123!"),
        role="Employee",
        department="Engineering",
        is_active=True,
    )

    db.add_all([admin, manager, employee])
    db.commit()

    upload_dir = tmp_path / "uploads"

    monkeypatch.setattr(
        upload_settings,
        "UPLOAD_DIR",
        str(upload_dir),
    )

    monkeypatch.setattr(
        upload_settings,
        "MAX_UPLOAD_SIZE_MB",
        1,
    )

    current_user = {
        "user_id": str(manager.id),
        "username": manager.username,
        "role": manager.role,
        "department": manager.department,
    }

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user

    client = TestClient(app)

    yield {
        "client": client,
        "db": db,
        "upload_dir": upload_dir,
        "current_user": current_user,
        "admin": admin,
        "manager": manager,
        "employee": employee,
    }

    client.close()
    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_manager_can_upload_txt(test_environment):
    client = test_environment["client"]

    response = client.post(
        "/documents/upload",
        data={"title": "Engineering Guide"},
        files={
            "file": (
                "guide.txt",
                b"Internal engineering documentation",
                "text/plain",
            )
        },
    )

    assert response.status_code == 201
    assert response.json()["filename"] == "guide.txt"
    assert response.json()["department"] == "Engineering"
    assert response.json()["allowed_roles"] == "Manager,Employee"
    assert "file_path" not in response.json()

    documents = test_environment["db"].query(Document).all()

    assert len(documents) == 1
    assert documents[0].filename == "guide.txt"


def test_upload_creates_audit_log(test_environment):
    response = test_environment["client"].post(
        "/documents/upload",
        data={"title": "Audited Engineering Guide"},
        files={
            "file": (
                "audited_guide.txt",
                b"Audit integration test document",
                "text/plain",
            )
        },
    )

    assert response.status_code == 201

    document_id = response.json()["id"]
    db = test_environment["db"]

    audit_entry = (
        db.query(AuditLog)
        .filter(
            AuditLog.action == "DOCUMENT_UPLOAD",
            AuditLog.resource_type == "Document",
            AuditLog.resource_id == str(document_id),
        )
        .first()
    )

    assert audit_entry is not None
    assert audit_entry.user_id == test_environment["manager"].id
    assert audit_entry.username == "test_manager"
    assert audit_entry.details == "Document uploaded successfully"


def test_manager_cannot_assign_admin_access(test_environment):
    response = test_environment["client"].post(
        "/documents/upload",
        data={
            "title": "Restricted Guide",
            "allowed_roles": "Admin,Manager",
        },
        files={
            "file": (
                "guide.txt",
                b"Restricted documentation",
                "text/plain",
            )
        },
    )

    assert response.status_code == 403
    assert test_environment["db"].query(Document).count() == 0


def test_manager_cannot_upload_to_another_department(test_environment):
    response = test_environment["client"].post(
        "/documents/upload",
        data={
            "title": "Department Guide",
            "department": "Finance",
        },
        files={
            "file": (
                "guide.txt",
                b"Department documentation",
                "text/plain",
            )
        },
    )

    assert response.status_code == 201
    assert response.json()["department"] == "Engineering"


def test_upload_rejects_unsupported_extension(test_environment):
    response = test_environment["client"].post(
        "/documents/upload",
        data={"title": "Executable"},
        files={
            "file": (
                "malware.exe",
                b"not an executable",
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 415


def test_upload_rejects_invalid_pdf_signature(test_environment):
    response = test_environment["client"].post(
        "/documents/upload",
        data={"title": "Invalid PDF"},
        files={
            "file": (
                "invalid.pdf",
                b"This is not a PDF file",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 415


def test_upload_rejects_oversized_file(test_environment):
    response = test_environment["client"].post(
        "/documents/upload",
        data={"title": "Large File"},
        files={
            "file": (
                "large.txt",
                b"A" * (1024 * 1024 + 1),
                "text/plain",
            )
        },
    )

    assert response.status_code == 413


def test_upload_rejects_empty_file(test_environment):
    response = test_environment["client"].post(
        "/documents/upload",
        data={"title": "Empty File"},
        files={
            "file": (
                "empty.txt",
                b"",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400
