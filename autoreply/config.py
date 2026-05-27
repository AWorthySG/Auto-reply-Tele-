"""Configuration loading and validation.

Loads runtime settings from a YAML file into plain dataclasses. Kept free of any
Telethon imports so the decision logic can be tested in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import yaml


class ConfigError(Exception):
    """Raised when the config file is missing required values or malformed."""


@dataclass(frozen=True)
class Rule:
    keywords: tuple[str, ...]
    reply: str


@dataclass(frozen=True)
class Config:
    away_enabled: bool
    inactivity_minutes: float
    cooldown_minutes: float
    private_enabled: bool
    groups_enabled: bool
    groups_only_when_mentioned: bool
    rules: tuple[Rule, ...]
    default_reply: str | None
    signature: str
    ignore_user_ids: frozenset[int]
    ignore_chat_ids: frozenset[int]


def _as_bool(value: object, path: str, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ConfigError(f"{path} must be true or false, got {value!r}")


def _as_number(value: object, path: str, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{path} must be a number, got {value!r}")
    if value < 0:
        raise ConfigError(f"{path} must not be negative, got {value!r}")
    return float(value)


def _as_id_set(value: object, path: str) -> frozenset[int]:
    if value is None:
        return frozenset()
    if not isinstance(value, list):
        raise ConfigError(f"{path} must be a list of integer IDs")
    ids: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int):
            raise ConfigError(f"{path} must contain only integer IDs, got {item!r}")
        ids.append(item)
    return frozenset(ids)


def _parse_rules(raw: object) -> tuple[Rule, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ConfigError("rules must be a list")
    rules: list[Rule] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ConfigError(f"rules[{i}] must be a mapping with 'keywords' and 'reply'")
        keywords_raw = entry.get("keywords")
        if not isinstance(keywords_raw, list) or not keywords_raw:
            raise ConfigError(f"rules[{i}].keywords must be a non-empty list")
        keywords: list[str] = []
        for kw in keywords_raw:
            if not isinstance(kw, str) or not kw.strip():
                raise ConfigError(f"rules[{i}].keywords must contain non-empty strings")
            keywords.append(kw.strip().lower())
        reply = entry.get("reply")
        if not isinstance(reply, str) or not reply.strip():
            raise ConfigError(f"rules[{i}].reply must be a non-empty string")
        rules.append(Rule(keywords=tuple(keywords), reply=reply))
    return tuple(rules)


def parse_config(data: dict) -> Config:
    """Build a Config from an already-parsed YAML mapping. Pure / testable."""
    if not isinstance(data, dict):
        raise ConfigError("config root must be a mapping")

    away = data.get("away") or {}
    cooldown = data.get("cooldown") or {}
    private_chats = data.get("private_chats") or {}
    groups = data.get("groups") or {}
    ignore = data.get("ignore") or {}

    default_reply = data.get("default_reply")
    if default_reply is not None and not isinstance(default_reply, str):
        raise ConfigError("default_reply must be a string or null")

    signature = data.get("signature")
    if signature is None:
        signature = ""
    elif not isinstance(signature, str):
        raise ConfigError("signature must be a string or null")

    rules = _parse_rules(data.get("rules"))
    if not rules and not default_reply:
        raise ConfigError(
            "No way to reply: define at least one rule or a default_reply."
        )

    return Config(
        away_enabled=_as_bool(away.get("enabled"), "away.enabled", True),
        inactivity_minutes=_as_number(
            away.get("inactivity_minutes"), "away.inactivity_minutes", 15.0
        ),
        cooldown_minutes=_as_number(
            cooldown.get("minutes"), "cooldown.minutes", 240.0
        ),
        private_enabled=_as_bool(
            private_chats.get("enabled"), "private_chats.enabled", True
        ),
        groups_enabled=_as_bool(groups.get("enabled"), "groups.enabled", True),
        groups_only_when_mentioned=_as_bool(
            groups.get("only_when_mentioned"), "groups.only_when_mentioned", True
        ),
        rules=rules,
        default_reply=default_reply,
        signature=signature,
        ignore_user_ids=_as_id_set(ignore.get("user_ids"), "ignore.user_ids"),
        ignore_chat_ids=_as_id_set(ignore.get("chat_ids"), "ignore.chat_ids"),
    )


def load_config(path: str) -> Config:
    """Read and validate the YAML config at ``path``."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except FileNotFoundError as exc:
        raise ConfigError(
            f"Config file not found: {path}. Copy config.example.yaml to {path}."
        ) from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"Could not parse {path}: {exc}") from exc
    return parse_config(data or {})
