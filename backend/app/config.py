import os
from pathlib import Path

from fastapi import HTTPException

DEFAULT_DB_PATH = Path("/app/data/pm.db")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-oss-120b"


def get_db_path() -> Path:
    from app.main import app  # lazy import to avoid circular dependency
    if hasattr(app.state, "db_path"):
        return Path(app.state.db_path)
    env_path = os.environ.get("PM_DB_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_DB_PATH


def get_openrouter_key() -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="missing_openrouter_key")
    return api_key
