import os
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv
from nemoguardrails import RailsConfig, LLMRails
from backend.core.config import settings
PROJECT_ROOT = Path(__file__).resolve().parents[2]
GUARDRAILS_CONFIG_PATH = PROJECT_ROOT / "config" / "guardrails"
def load_guardrail_environment() -> None:
    """Load the project environment variables for NeMo."""
    load_dotenv(PROJECT_ROOT / ".env")
    if not os.getenv("GROQ_API_KEY") and settings.GROQ_API_KEY:
        os.environ["GROQ_API_KEY"] = settings.GROQ_API_KEY
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY is not configured.")
def validate_guardrails_config() -> bool:
    """Validate the NeMo configuration without making an LLM request."""
    load_guardrail_environment()
    config = RailsConfig.from_path(str(GUARDRAILS_CONFIG_PATH))
    return config is not None
@lru_cache(maxsize=1)
def get_guardrails() -> LLMRails:
    """Load and cache the NeMo Guardrails engine."""
    load_guardrail_environment()
    config = RailsConfig.from_path(str(GUARDRAILS_CONFIG_PATH))
    return LLMRails(config)
