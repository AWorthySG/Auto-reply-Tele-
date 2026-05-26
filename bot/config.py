import os

from dotenv import load_dotenv

load_dotenv()


def _parse_admin_ids(raw: str) -> set[int]:
    ids: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part:
            ids.add(int(part))
    return ids


TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_IDS = _parse_admin_ids(os.environ.get("ADMIN_IDS", ""))

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
ANTHROPIC_MAX_TOKENS = int(os.environ.get("ANTHROPIC_MAX_TOKENS", "400"))

DATABASE_PATH = os.environ.get("DATABASE_PATH", "bot.db")

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful, concise assistant replying on behalf of a Telegram chat. "
    "Keep replies short, friendly, and directly useful. If you are unsure, say so briefly."
)


def require_token() -> str:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env and fill it in."
        )
    return TELEGRAM_BOT_TOKEN
