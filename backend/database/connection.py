
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.core.config import settings


class Base(DeclarativeBase):
    """Base class for all database models."""


# Normalize Render PostgreSQL URLs for SQLAlchemy and psycopg2.
raw_database_url = settings.DATABASE_URL

if raw_database_url.startswith("postgres://"):
    database_url_string = raw_database_url.replace(
        "postgres://",
        "postgresql+psycopg2://",
        1,
    )
elif raw_database_url.startswith("postgresql://"):
    database_url_string = raw_database_url.replace(
        "postgresql://",
        "postgresql+psycopg2://",
        1,
    )
else:
    database_url_string = raw_database_url

database_url = make_url(database_url_string)

connect_args = {}

if database_url.drivername.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

    database_path = database_url.database

    if database_path and database_path != ":memory:":
        if not database_path.startswith("file:"):
            Path(database_path).expanduser().parent.mkdir(
                parents=True,
                exist_ok=True,
            )

engine = create_engine(
    database_url_string,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db():
    """Provide a database session and close it after the request."""
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
