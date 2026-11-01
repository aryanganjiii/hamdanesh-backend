"""Typed application settings loaded from the backend .env and process env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


# In the standalone backend repository, this is the repository root. When the
# backend runs inside the original frontend/backend workspace, it remains the
# backend directory while the environment file can fall back to the workspace.
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


def _read_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        return max(minimum, min(maximum, int(os.getenv(name, str(default)))))
    except ValueError:
        return default


def _read_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    project_root: Path
    database_path: Path
    sample_documents_path: Path
    api_key: str
    base_url: str
    chat_model: str
    embedding_model: str
    timeout_seconds: int
    max_output_tokens: int
    ai_enabled: bool
    max_message_chars: int
    history_messages: int
    max_file_bytes: int
    chunk_size: int
    chunk_overlap: int
    port: int

    @classmethod
    def from_environment(cls) -> "Settings":
        env_path = PROJECT_ROOT / ".env"
        workspace_env_path = PROJECT_ROOT.parent / ".env"
        if not env_path.is_file() and (PROJECT_ROOT.parent / "frontend").is_dir():
            env_path = workspace_env_path
        _load_env_file(env_path)
        default_db = PROJECT_ROOT / "data" / "knowledge.sqlite3"
        configured_db = Path(os.getenv("KNOWLEDGE_DB_PATH", str(default_db)))
        if not configured_db.is_absolute():
            configured_db = PROJECT_ROOT / configured_db
        return cls(
            project_root=PROJECT_ROOT,
            database_path=configured_db,
            sample_documents_path=PROJECT_ROOT / "sample_documents",
            api_key=os.getenv("AVALAI_API_KEY", "").strip(),
            base_url=os.getenv("AVALAI_BASE_URL", "https://api.avalai.ir/v1").rstrip("/"),
            chat_model=os.getenv("AVALAI_CHAT_MODEL", "gpt-5.4-mini"),
            embedding_model=os.getenv("AVALAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            timeout_seconds=_read_int("AVALAI_TIMEOUT_SECONDS", 90, 5, 300),
            max_output_tokens=_read_int("AVALAI_MAX_OUTPUT_TOKENS", 900, 100, 8000),
            ai_enabled=_read_bool("AI_ASSISTANT_ENABLED", True),
            max_message_chars=_read_int("AI_ASSISTANT_MAX_MESSAGE_CHARS", 1000, 100, 10000),
            history_messages=_read_int("AI_ASSISTANT_HISTORY_MESSAGES", 12, 0, 40),
            max_file_bytes=_read_int("DOCUMENT_MAX_BYTES", 12 * 1024 * 1024, 1024, 32 * 1024 * 1024),
            chunk_size=_read_int("RAG_CHUNK_SIZE", 1800, 400, 6000),
            chunk_overlap=_read_int("RAG_CHUNK_OVERLAP", 220, 0, 1200),
            port=_read_int("PORT", 8000, 1, 65535),
        )

    @property
    def provider_configured(self) -> bool:
        return bool(self.api_key)
