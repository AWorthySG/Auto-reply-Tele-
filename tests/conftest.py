"""Shared helpers for building configs in tests."""

from __future__ import annotations

from autoreply.config import Config, parse_config

_BASE = {
    "away": {"enabled": True, "inactivity_minutes": 15},
    "cooldown": {"minutes": 240},
    "private_chats": {"enabled": True},
    "groups": {"enabled": True, "only_when_mentioned": True},
    "rules": [
        {"keywords": ["price", "cost"], "reply": "PRICE_REPLY"},
        {"keywords": ["meeting"], "reply": "MEETING_REPLY"},
    ],
    "default_reply": "DEFAULT_REPLY",
    "signature": "",
    "ignore": {"user_ids": [], "chat_ids": []},
}


def make_config(**overrides) -> Config:
    """Build a Config, deep-merging one level of overrides onto a sane base."""
    data = {key: (value.copy() if isinstance(value, dict) else value) for key, value in _BASE.items()}
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(data.get(key), dict):
            merged = data[key].copy()
            merged.update(value)
            data[key] = merged
        else:
            data[key] = value
    return parse_config(data)
