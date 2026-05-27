"""Entry point: connect as the personal account and auto-reply when away.

Run modes:
  python -m autoreply.main            # connect to Telegram and run
  python -m autoreply.main --dry-run  # no network; print decisions for samples
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
from collections import deque

from dotenv import load_dotenv

from .config import Config, ConfigError, load_config
from .engine import IncomingMessage, decide_reply
from .state import State

log = logging.getLogger("autoreply")

DEFAULT_CONFIG_PATH = "config.yaml"
EXAMPLE_CONFIG_PATH = "config.example.yaml"
DEFAULT_STATE_PATH = "state.json"


def _resolve_config_path() -> str:
    return os.environ.get("CONFIG_PATH") or DEFAULT_CONFIG_PATH


def _resolve_state_path() -> str:
    return os.environ.get("STATE_PATH") or DEFAULT_STATE_PATH


def _load_config_with_fallback(path: str) -> tuple[Config, str]:
    """Load config from ``path``; fall back to the example file if absent.

    The fallback exists so `--dry-run` works before a user writes config.yaml.
    """
    if os.path.exists(path):
        return load_config(path), path
    if os.path.exists(EXAMPLE_CONFIG_PATH):
        log.warning("%s not found; using %s for this run.", path, EXAMPLE_CONFIG_PATH)
        return load_config(EXAMPLE_CONFIG_PATH), EXAMPLE_CONFIG_PATH
    raise ConfigError(
        f"No config found. Copy {EXAMPLE_CONFIG_PATH} to {path} and edit it."
    )


# --------------------------------------------------------------------------
# Dry run: exercise decide_reply on representative messages, no Telegram.
# --------------------------------------------------------------------------
def run_dry_run(config: Config) -> int:
    now = 100_000.0
    state_path = _resolve_state_path()
    away = State(path=state_path, last_self_activity=now - 3600, last_reply={})
    active = State(path=state_path, last_self_activity=now - 30, last_reply={})

    cooled = State(path=state_path, last_self_activity=now - 3600, last_reply={})
    cooled.record_reply(chat_id=1, now=now - 60)

    samples: list[tuple[str, IncomingMessage, State]] = [
        (
            "private, no keyword, away",
            IncomingMessage(chat_id=1, text="hey are you there?", is_private=True, is_group=False, sender_id=1),
            away,
        ),
        (
            "private, 'price' keyword, away",
            IncomingMessage(chat_id=2, text="what's your price?", is_private=True, is_group=False, sender_id=2),
            away,
        ),
        (
            "private, but user is ACTIVE",
            IncomingMessage(chat_id=3, text="hello", is_private=True, is_group=False, sender_id=3),
            active,
        ),
        (
            "group, NOT mentioned, away",
            IncomingMessage(chat_id=-100, text="general chatter", is_private=False, is_group=True, sender_id=9),
            away,
        ),
        (
            "group, mentioned, away",
            IncomingMessage(chat_id=-100, text="@you any availability for a meeting?", is_private=False, is_group=True, sender_id=9, is_mention=True),
            away,
        ),
        (
            "private, away but in cooldown",
            IncomingMessage(chat_id=1, text="still there?", is_private=True, is_group=False, sender_id=1),
            cooled,
        ),
    ]

    print("DRY RUN — no messages are sent.\n")
    for label, msg, state in samples:
        reply = decide_reply(msg, state, config, now)
        verdict = f"REPLY: {reply!r}" if reply is not None else "no reply"
        print(f"- {label}\n    -> {verdict}\n")
    return 0


# --------------------------------------------------------------------------
# Live run.
# --------------------------------------------------------------------------
async def run_live(config: Config) -> int:
    from telethon import TelegramClient, events  # imported lazily so --dry-run needs no telethon

    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")
    session_name = os.environ.get("SESSION_NAME", "autoreply")
    if not api_id or not api_hash:
        log.error("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set (see .env.example).")
        return 1

    state = State.load(_resolve_state_path(), now=time.time())
    # Track ids of messages WE auto-send so they don't count as "user activity".
    sent_ids: set[int] = set()
    sent_order: deque[int] = deque(maxlen=2000)

    def remember_sent(message_id: int) -> None:
        if len(sent_order) == sent_order.maxlen:
            sent_ids.discard(sent_order[0])
        sent_order.append(message_id)
        sent_ids.add(message_id)

    client = TelegramClient(session_name, int(api_id), api_hash)
    await client.start()
    me = await client.get_me()
    my_id = me.id
    log.info("Logged in as %s (id=%s). Auto-reply running. Press Ctrl+C to stop.", me.first_name, my_id)

    @client.on(events.NewMessage(outgoing=True))
    async def on_outgoing(event):
        # Any message YOU send (manually) counts as activity and resets the away
        # timer. Skip messages the bot itself auto-sent.
        if event.message.id in sent_ids:
            return
        state.touch_activity(time.time())
        state.save()

    @client.on(events.NewMessage(incoming=True))
    async def on_incoming(event):
        now = time.time()
        sender_id = event.sender_id

        # Never reply to other bots.
        try:
            sender = await event.get_sender()
            if getattr(sender, "bot", False):
                return
        except Exception:  # noqa: BLE001 - sender fetch is best-effort
            pass

        is_reply_to_me = False
        if event.is_reply:
            try:
                replied = await event.get_reply_message()
                is_reply_to_me = replied is not None and replied.sender_id == my_id
            except Exception:  # noqa: BLE001
                is_reply_to_me = False

        msg = IncomingMessage(
            chat_id=event.chat_id,
            text=event.raw_text or "",
            is_private=event.is_private,
            is_group=event.is_group,
            sender_id=sender_id,
            is_mention=bool(getattr(event.message, "mentioned", False)),
            is_reply_to_me=is_reply_to_me,
        )

        reply = decide_reply(msg, state, config, now)
        if reply is None:
            return

        try:
            sent = await event.reply(reply)
        except Exception as exc:  # noqa: BLE001 - keep running on send errors
            log.warning("Failed to send auto-reply to chat %s: %s", msg.chat_id, exc)
            return

        if sent is not None:
            remember_sent(sent.id)
        state.record_reply(msg.chat_id, now)
        state.save()
        log.info("Auto-replied in chat %s", msg.chat_id)

    async with client:
        await client.run_until_disconnected()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Personal Telegram auto-reply userbot.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't connect to Telegram; print reply decisions for sample messages.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging."
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    load_dotenv()

    try:
        config, used = _load_config_with_fallback(_resolve_config_path())
    except ConfigError as exc:
        log.error("%s", exc)
        return 2

    if args.dry_run:
        log.info("Config loaded from %s", used)
        return run_dry_run(config)

    try:
        return asyncio.run(run_live(config))
    except KeyboardInterrupt:
        log.info("Stopped.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
