
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.main import app
from backend.auth.dependencies import get_current_user
from backend.database.connection import Base, get_db
from backend.models.user import User
from backend.models.document import Document
from backend.models.audit_log import AuditLog
from backend.auth.security import hash_password


@pytest.fixture
def delete_environment(tmp_path):
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
        username="delete_admin",
        email="delete_admin@example.test",
        hashed_password=hash_password("TestPassword123!"),
        role="Admin",
        department="General",
        is_active=True,
    )

    employee = User(
        username="delete_employee",
        email="delete_employee@example.test",
        hashed_password=hash_password("TestPassword123!"),
        role="Employee",
        department="Engineering",
        is_active=True,
    )

    manager = User(
        username="delete_manager",
        email="delete_manager@example.test",
        hashed_password=hash_password("TestPassword123!"),
        role="Manager",
        department="Engineering",
        is_active=True,
    )

    db.add_all([admin, employee, manager])
    db.commit()

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True)

    document_file = upload_dir / "delete_test.txt"
    document_file.write_text(
        "Confidential document content",
        encoding="utf-8",
    )

    document = Document(
        title="Delete Test Document",
        filename="delete_test.txt",
        file_path=str(document_file),
        content_type="text/plain",
        owner_id=admin.id,
        department="Engineering",
        allowed_roles="Admin,Manager,Employee",
        is_active=True,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

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
        "document": document,
        "document_file": document_file,
        "current_user": current_user,
        "admin": admin,
    }

    client.close()
    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_admin_can_soft_delete_document(delete_environment):
    response = delete_environment["client"].delete(
        f"/documents/{delete_environment['document'].id}"
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False

    delete_environment["db"].refresh(
        delete_environment["document"]
    )

    assert delete_environment["document"].is_active is False


def test_soft_delete_creates_audit_log(delete_environment):
    document_id = delete_environment["document"].id

    response = delete_environment["client"].delete(
        f"/documents/{document_id}"
    )

    assert response.status_code == 200

    db = delete_environment["db"]

    audit_entry = (
        db.query(AuditLog)
        .filter(
            AuditLog.action == "DOCUMENT_DELETE",
            AuditLog.resource_type == "Document",
            AuditLog.resource_id == str(document_id),
        )
        .first()
    )

    assert audit_entry is not None
    assert audit_entry.user_id == delete_environment["admin"].id
    assert audit_entry.username == "delete_admin"
    assert audit_entry.details == "Document soft-deleted successfully"


@pytest.mark.parametrize(
    "role,username",
    [
        ("Employee", "delete_employee"),
        ("Manager", "delete_manager"),
    ],
)
def test_non_admin_cannot_soft_delete_document(
    delete_environment,
    role,
    username,
):
    delete_environment["current_user"].update(
        {
            "username": username,
            "role": role,
            "user_id": "2" if role == "Employee" else "3",
            "department": "Engineering",
        }
    )

    response = delete_environment["client"].delete(
        f"/documents/{delete_environment['document'].id}"
    )

    assert response.status_code == 403
    assert delete_environment["document"].is_active is True


def test_soft_deleted_document_is_hidden_from_listing(
    delete_environment,
):
    client = delete_environment["client"]
    document_id = delete_environment["document"].id

    delete_response = client.delete(
        f"/documents/{document_id}"
    )

    assert delete_response.status_code == 200

    listing_response = client.get("/documents")

    assert listing_response.status_code == 200

    document_ids = [
        item["id"] for item in listing_response.json()
    ]

    assert document_id not in document_ids


def test_soft_deleted_document_cannot_be_downloaded(
    delete_environment,
):
    client = delete_environment["client"]
    document_id = delete_environment["document"].id

    delete_response = client.delete(
        f"/documents/{document_id}"
    )

    assert delete_response.status_code == 200

    download_response = client.get(
        f"/documents/{document_id}/download"
    )

    assert download_response.status_code == 404


def test_soft_delete_preserves_original_file(
    delete_environment,
):
    document_id = delete_environment["document"].id
    document_file = delete_environment["document_file"]

    response = delete_environment["client"].delete(
        f"/documents/{document_id}"
    )

    assert response.status_code == 200
    assert document_file.exists()
    assert document_file.read_text(
        encoding="utf-8"
    ) == "Confidential document content"
