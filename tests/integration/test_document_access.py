
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.main import app
from backend.api.document_routes import settings as document_settings
from backend.auth.dependencies import get_current_user
from backend.database.connection import Base, get_db
from backend.models.user import User
from backend.models.document import Document
from backend.auth.security import hash_password


@pytest.fixture
def access_environment(tmp_path, monkeypatch):
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

    employee = User(
        username="access_employee",
        email="access_employee@example.test",
        hashed_password=hash_password("TestPassword123!"),
        role="Employee",
        department="Engineering",
        is_active=True,
    )

    admin = User(
        username="access_admin",
        email="access_admin@example.test",
        hashed_password=hash_password("TestPassword123!"),
        role="Admin",
        department="General",
        is_active=True,
    )

    db.add_all([employee, admin])
    db.commit()

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True)

    monkeypatch.setattr(
        document_settings,
        "UPLOAD_DIR",
        str(upload_dir),
    )

    accessible_file = upload_dir / "engineering.txt"
    accessible_file.write_text(
        "Engineering confidential guide",
        encoding="utf-8",
    )

    restricted_file = upload_dir / "finance.txt"
    restricted_file.write_text(
        "Finance confidential guide",
        encoding="utf-8",
    )

    accessible_document = Document(
        title="Engineering Guide",
        filename="engineering.txt",
        file_path=str(accessible_file),
        content_type="text/plain",
        owner_id=employee.id,
        department="Engineering",
        allowed_roles="Employee,Manager",
        is_active=True,
    )

    restricted_document = Document(
        title="Finance Guide",
        filename="finance.txt",
        file_path=str(restricted_file),
        content_type="text/plain",
        owner_id=admin.id,
        department="Finance",
        allowed_roles="Employee,Manager",
        is_active=True,
    )

    db.add_all([accessible_document, restricted_document])
    db.commit()
    db.refresh(accessible_document)
    db.refresh(restricted_document)

    current_user = {
        "user_id": str(employee.id),
        "username": employee.username,
        "role": employee.role,
        "department": employee.department,
    }

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user

    client = TestClient(app)

    yield {
        "client": client,
        "db": db,
        "accessible_document": accessible_document,
        "restricted_document": restricted_document,
        "accessible_file": accessible_file,
        "current_user": current_user,
    }

    client.close()
    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_employee_can_list_accessible_documents(access_environment):
    response = access_environment["client"].get("/documents")

    assert response.status_code == 200

    documents = response.json()

    assert len(documents) == 1
    assert documents[0]["title"] == "Engineering Guide"
    assert "file_path" not in documents[0]


def test_employee_cannot_see_other_department_documents(access_environment):
    response = access_environment["client"].get("/documents")

    titles = [item["title"] for item in response.json()]

    assert "Finance Guide" not in titles


def test_employee_can_download_accessible_document(access_environment):
    document = access_environment["accessible_document"]

    response = access_environment["client"].get(
        f"/documents/{document.id}/download"
    )

    assert response.status_code == 200
    assert response.content == b"Engineering confidential guide"
    assert "engineering.txt" in response.headers.get(
        "content-disposition",
        "",
    )


def test_employee_cannot_download_other_department_document(access_environment):
    document = access_environment["restricted_document"]

    response = access_environment["client"].get(
        f"/documents/{document.id}/download"
    )

    assert response.status_code == 404


def test_download_rejects_missing_document(access_environment):
    response = access_environment["client"].get(
        "/documents/99999/download"
    )

    assert response.status_code == 404


def test_download_rejects_file_outside_upload_directory(
    access_environment,
    tmp_path,
    monkeypatch,
):
    document = access_environment["accessible_document"]

    outside_file = tmp_path / "outside.txt"
    outside_file.write_text(
        "This file must not be downloadable",
        encoding="utf-8",
    )

    document.file_path = str(outside_file)
    access_environment["db"].commit()

    response = access_environment["client"].get(
        f"/documents/{document.id}/download"
    )

    assert response.status_code == 404
