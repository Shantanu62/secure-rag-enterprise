
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database.connection import Base
from backend.models.user import User
from backend.models.audit_log import AuditLog
from backend.auth.security import hash_password
from backend.security.audit_service import record_audit_event


@pytest.fixture
def audit_db():
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

    user = User(
        username="audit_test_user",
        email="audit_test@example.test",
        hashed_password=hash_password("TestPassword123!"),
        role="Admin",
        department="General",
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    yield db, user

    db.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_record_audit_event_creates_entry(audit_db):
    db, user = audit_db

    current_user = {
        "user_id": str(user.id),
        "username": user.username,
        "role": user.role,
    }

    audit_entry = record_audit_event(
        db=db,
        current_user=current_user,
        action="DOCUMENT_UPLOAD",
        resource_type="Document",
        resource_id=101,
        details="Document uploaded successfully",
        ip_address="127.0.0.1",
    )

    db.commit()
    db.refresh(audit_entry)

    assert audit_entry.id is not None
    assert audit_entry.user_id == user.id
    assert audit_entry.username == user.username
    assert audit_entry.action == "DOCUMENT_UPLOAD"
    assert audit_entry.resource_type == "Document"
    assert audit_entry.resource_id == "101"
    assert audit_entry.ip_address == "127.0.0.1"


def test_record_audit_event_supports_optional_fields(audit_db):
    db, user = audit_db

    audit_entry = record_audit_event(
        db=db,
        current_user={
            "user_id": str(user.id),
            "username": user.username,
        },
        action="DOCUMENT_DELETE",
        resource_type="Document",
    )

    db.commit()
    db.refresh(audit_entry)

    assert audit_entry.resource_id is None
    assert audit_entry.details is None
    assert audit_entry.ip_address is None


def test_audit_event_is_not_committed_automatically(audit_db):
    db, user = audit_db

    audit_entry = record_audit_event(
        db=db,
        current_user={
            "user_id": str(user.id),
            "username": user.username,
        },
        action="DOCUMENT_UPLOAD",
        resource_type="Document",
    )

    # The audit service should only add the entry to the session.
    assert audit_entry in db.new

    # Explicit flush makes the pending entry visible in the transaction.
    db.flush()
    assert db.query(AuditLog).count() == 1

    # Rollback should remove the uncommitted entry.
    db.rollback()
    assert db.query(AuditLog).count() == 0


def test_audit_event_supports_missing_user_id(audit_db):
    db, _ = audit_db

    audit_entry = record_audit_event(
        db=db,
        current_user={"username": "deleted_user"},
        action="SYSTEM_EVENT",
        resource_type="System",
    )

    db.commit()
    db.refresh(audit_entry)

    assert audit_entry.user_id is None
    assert audit_entry.username == "deleted_user"


def test_audit_event_rejects_invalid_user_id_gracefully(audit_db):
    db, _ = audit_db

    audit_entry = record_audit_event(
        db=db,
        current_user={
            "user_id": "invalid",
            "username": "unknown_user",
        },
        action="SYSTEM_EVENT",
        resource_type="System",
    )

    db.commit()
    db.refresh(audit_entry)

    assert audit_entry.user_id is None
    assert audit_entry.username == "unknown_user"
