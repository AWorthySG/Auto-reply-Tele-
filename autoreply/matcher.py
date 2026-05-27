"""Keyword matching. Pure functions, no I/O."""

from __future__ import annotations

from .config import Config


def match_rule_reply(text: str, config: Config) -> str | None:
    """Return the reply body for ``text`` based on keyword rules.

    First rule whose keywords appear (case-insensitive substring) in the text
    wins. Falls back to ``default_reply``. Returns None if nothing matches and
    there is no default. The signature is NOT applied here.
    """
    haystack = (text or "").lower()
    for rule in config.rules:
        if any(keyword in haystack for keyword in rule.keywords):
            return rule.reply
    return config.default_reply
