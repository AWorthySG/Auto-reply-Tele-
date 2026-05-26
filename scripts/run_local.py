"""Run the bot locally using long polling.

    python -m scripts.run_local

Requires TELEGRAM_BOT_TOKEN in your environment or .env file.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.app import build_application  # noqa: E402


def main() -> None:
    app = build_application()
    print("Bot started (long polling). Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
