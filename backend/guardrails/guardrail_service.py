import os
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv
from nemoguardrails import Guardrails, RailsConfig
from backend.core.config import settings
PROJECT_ROOT = Path(__file__).resolve().parents[2]
GUARDRAILS_CONFIG_PATH = PROJECT_ROOT / "config" / "guardrails"
def load_guardrail_environment():
    load_dotenv(PROJECT_ROOT / ".env")
    if not os.getenv("GROQ_API_KEY") and settings.GROQ_API_KEY:
        os.environ["GROQ_API_KEY"] = settings.GROQ_API_KEY
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY is not configured.")
def validate_guardrails_config():
    load_guardrail_environment()
    config = RailsConfig.from_path(str(GUARDRAILS_CONFIG_PATH))
    from nemoguardrails.guardrails.iorails import IORails
    reason = IORails.unsupported_reason(config)
    if reason is not None:
        raise RuntimeError(f"IORails cannot serve this configuration: {reason}")
    return True
@lru_cache(maxsize=1)
def get_guardrails() -> Guardrails:
    load_guardrail_environment()
    config = RailsConfig.from_path(str(GUARDRAILS_CONFIG_PATH))
    return Guardrails(config, use_iorails=True, require_iorails=True)
