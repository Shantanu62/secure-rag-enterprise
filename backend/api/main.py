
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from backend.api.auth_routes import router as auth_router
from backend.api.document_routes import router as document_router
from backend.api.audit_routes import router as audit_router
from backend.api.chat_routes import router as chat_router
from backend.core.config import settings
from backend.database.connection import Base, engine
import backend.models


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables when the application starts."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Production-oriented RAG platform with RBAC, "
        "NeMo Guardrails, and PII Scrubbing."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(document_router)
app.include_router(audit_router)
app.include_router(chat_router)


@app.get("/", tags=["General"])
def root():
    return {
        "message": "Production RAG API is running",
        "application": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }


@app.get("/health", tags=["General"])
def health_check():
    return {
        "status": "healthy",
        "service": "Production RAG API",
    }


@app.get("/health/database", tags=["General"])
def database_health_check():
    """Verify that the configured database can execute a query."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
            "driver": engine.dialect.name,
        }

    except Exception:
        logger.exception("Database health check failed.")
        raise HTTPException(
            status_code=503,
            detail="Database connection failed.",
        ) from None
