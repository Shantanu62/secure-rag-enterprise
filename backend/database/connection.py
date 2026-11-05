from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from backend.core.config import settings
class Base(DeclarativeBase):
    """Base class for all database models."""
database_url = make_url(settings.DATABASE_URL)
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
    settings.DATABASE_URL,
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
