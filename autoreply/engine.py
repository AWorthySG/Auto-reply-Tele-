"""The core decision: given an incoming message and current state, what (if
anything) should we auto-reply?

This is intentionally a pure function operating on plain data so it can be unit
tested and exercised in --dry-run mode without any Telegram connection. The
Telethon layer in main.py builds an IncomingMessage and calls decide_reply.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import Config
from .matcher import match_rule_reply
from .state import State


@dataclass(frozen=True)
class IncomingMessage:
    chat_id: int
    text: str
    is_private: bool
    is_group: bool
    sender_id: int | None = None
    is_mention: bool = False  # the account is @mentioned in this message
    is_reply_to_me: bool = False  # the message replies to one of the account's messages


def decide_reply(
    msg: IncomingMessage,
    state: State,
    config: Config,
    now: float,
) -> str | None:
    """Return the full reply text to send, or None to stay silent.

    Does not mutate state; the caller records the reply after sending succeeds.
    """
    if not (msg.text or "").strip():
        return None

    if msg.sender_id is not None and msg.sender_id in config.ignore_user_ids:
        return None
    if msg.chat_id in config.ignore_chat_ids:
        return None

    # Away gate: only reply when the account owner has been inactive.
    if config.away_enabled and not state.is_away(now, config.inactivity_minutes):
        return None

    # Chat-type gating.
    if msg.is_private:
        if not config.private_enabled:
            return None
    elif msg.is_group:
        if not config.groups_enabled:
            return None
        if config.groups_only_when_mentioned and not (msg.is_mention or msg.is_reply_to_me):
            return None
    else:
        # Channels / unknown peer types: never auto-reply.
        return None

    # Per-chat cooldown to avoid loops and spam.
    if state.in_cooldown(msg.chat_id, now, config.cooldown_minutes):
        return None

    body = match_rule_reply(msg.text, config)
    if body is None:
        return None

    return body + config.signature
