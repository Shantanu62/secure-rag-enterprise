import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.database.connection import Base
from backend.models.user import User
from backend.models.document import Document
from backend.auth.document_permissions import (
    get_accessible_documents,
    can_access_document,
)
@pytest.fixture
def db():
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
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
@pytest.fixture
def test_data(db):
    admin = User(
        username="test_admin",
        email="admin_test@example.com",
        hashed_password="test_hash",
        role="Admin",
        department="General",
        is_active=True,
    )
    employee = User(
        username="test_employee",
        email="employee_test@example.com",
        hashed_password="test_hash",
        role="Employee",
        department="Engineering",
        is_active=True,
    )
    db.add_all([admin, employee])
    db.flush()
    authorized_document = Document(
        title="Engineering Handbook",
        filename="engineering.txt",
        file_path="temporary/engineering.txt",
        content_type="text/plain",
        owner_id=admin.id,
        department="Engineering",
        allowed_roles="Employee,Manager",
        is_active=True,
    )
    wrong_department_document = Document(
        title="Finance Report",
        filename="finance.txt",
        file_path="temporary/finance.txt",
        content_type="text/plain",
        owner_id=employee.id,
        department="Finance",
        allowed_roles="Employee",
        is_active=True,
    )
    wrong_role_document = Document(
        title="Restricted Admin Document",
        filename="restricted.txt",
        file_path="temporary/restricted.txt",
        content_type="text/plain",
        owner_id=employee.id,
        department="Engineering",
        allowed_roles="Admin",
        is_active=True,
    )
    inactive_document = Document(
        title="Archived Document",
        filename="archived.txt",
        file_path="temporary/archived.txt",
        content_type="text/plain",
        owner_id=employee.id,
        department="Engineering",
        allowed_roles="Employee",
        is_active=False,
    )
    db.add_all([
        authorized_document,
        wrong_department_document,
        wrong_role_document,
        inactive_document,
    ])
    db.commit()
    return {
        "admin": {
            "user_id": admin.id,
            "role": "Admin",
            "department": "General",
        },
        "employee": {
            "user_id": employee.id,
            "role": "Employee",
            "department": "Engineering",
        },
        "authorized": authorized_document.id,
        "wrong_department": wrong_department_document.id,
        "wrong_role": wrong_role_document.id,
        "inactive": inactive_document.id,
    }
def test_admin_can_access_all_active_documents(db, test_data):
    documents = get_accessible_documents(db, test_data["admin"])
    assert len(documents) == 3
def test_employee_can_access_authorized_department_document(db, test_data):
    assert can_access_document(
        db,
        test_data["employee"],
        test_data["authorized"],
    )
def test_employee_cannot_access_other_department_document(db, test_data):
    assert not can_access_document(
        db,
        test_data["employee"],
        test_data["wrong_department"],
    )
def test_employee_cannot_access_unauthorized_role_document(db, test_data):
    assert not can_access_document(
        db,
        test_data["employee"],
        test_data["wrong_role"],
    )
def test_document_owner_cannot_bypass_department_restriction(db, test_data):
    assert not can_access_document(
        db,
        test_data["employee"],
        test_data["wrong_department"],
    )
def test_inactive_document_is_not_accessible_to_admin(db, test_data):
    assert not can_access_document(
        db,
        test_data["admin"],
        test_data["inactive"],
    )
def test_invalid_role_has_no_access(db, test_data):
    invalid_user = {
        "user_id": 999,
        "role": "SuperUser",
        "department": "Engineering",
    }
    assert get_accessible_documents(db, invalid_user) == []
    assert not can_access_document(
        db,
        invalid_user,
        test_data["authorized"],
    )
