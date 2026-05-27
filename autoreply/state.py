"""Persisted runtime state: last self-activity and per-chat reply timestamps.

Timestamps are POSIX seconds (float). State is persisted to a JSON file so that
the away/cooldown behavior survives restarts.
"""

from __future__ import annotations

import json
import os
import tempfile


class State:
    def __init__(self, path: str, last_self_activity: float, last_reply: dict[int, float]):
        self.path = path
        self.last_self_activity = last_self_activity
        # chat_id -> POSIX timestamp of last auto-reply we sent there
        self.last_reply = last_reply

    # --- persistence -----------------------------------------------------
    @classmethod
    def load(cls, path: str, now: float) -> "State":
        """Load state from ``path``; start fresh (active as of ``now``) if absent."""
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            return cls(path=path, last_self_activity=now, last_reply={})

        last_self_activity = data.get("last_self_activity")
        if not isinstance(last_self_activity, (int, float)):
            last_self_activity = now

        last_reply: dict[int, float] = {}
        raw = data.get("last_reply")
        if isinstance(raw, dict):
            for key, value in raw.items():
                try:
                    last_reply[int(key)] = float(value)
                except (TypeError, ValueError):
                    continue
        return cls(path=path, last_self_activity=float(last_self_activity), last_reply=last_reply)

    def save(self) -> None:
        """Atomically write state to disk."""
        data = {
            "last_self_activity": self.last_self_activity,
            "last_reply": {str(k): v for k, v in self.last_reply.items()},
        }
        directory = os.path.dirname(os.path.abspath(self.path)) or "."
        fd, tmp = tempfile.mkstemp(prefix=".state-", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            os.replace(tmp, self.path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    # --- queries / mutations --------------------------------------------
    def touch_activity(self, now: float) -> None:
        self.last_self_activity = now

    def is_away(self, now: float, inactivity_minutes: float) -> bool:
        return (now - self.last_self_activity) >= inactivity_minutes * 60.0

    def in_cooldown(self, chat_id: int, now: float, cooldown_minutes: float) -> bool:
        last = self.last_reply.get(chat_id)
        if last is None:
            return False
        return (now - last) < cooldown_minutes * 60.0

    def record_reply(self, chat_id: int, now: float) -> None:
        self.last_reply[chat_id] = now
