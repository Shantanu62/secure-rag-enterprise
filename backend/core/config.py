from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    APP_NAME: str = "Production RAG with RBAC, NeMo Guardrails & PII Scrubbing"
    APP_ENV: str = "development"
    DEBUG: bool = True
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = ""
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ADMIN_BOOTSTRAP_TOKEN: str = ""
    DATABASE_URL: str = "sqlite:///./secure_rag.db"
    VECTOR_STORE_PATH: str = "./data/vector_store"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150
    RETRIEVAL_TOP_K: int = 5
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    PII_MASKING_ENABLED: bool = True
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
@lru_cache
def get_settings() -> Settings:
    return Settings()
settings = get_settings()
