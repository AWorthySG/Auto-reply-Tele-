"""One-time interactive login.

Run this once: it prompts for the SMS code (and 2FA password if enabled) and
creates the "<SESSION_NAME>.session" file. After that, autoreply.main runs
unattended using that session.

    python login.py
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv


def main() -> int:
    load_dotenv()
    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")
    phone = os.environ.get("TELEGRAM_PHONE") or None
    session_name = os.environ.get("SESSION_NAME", "autoreply")

    if not api_id or not api_hash:
        print("Set TELEGRAM_API_ID and TELEGRAM_API_HASH first (copy .env.example to .env).")
        return 1

    from telethon import TelegramClient

    with TelegramClient(session_name, int(api_id), api_hash) as client:
        client.start(phone=phone)
        me = client.get_me()
        print(f"Logged in as {me.first_name} (@{me.username}, id={me.id}).")
        print(f"Session saved to {session_name}.session — you can now run: python -m autoreply.main")
    return 0


if __name__ == "__main__":
    sys.exit(main())
