import re
import sqlite3
from typing import Optional

from .. import db


def find_match(chat_id: int, text: str) -> Optional[sqlite3.Row]:
    """Return the first enabled rule whose pattern matches the text.

    Regex rules use a case-insensitive search; plain rules match if the
    keyword appears as a substring (case-insensitive)."""
    if not text:
        return None
    lowered = text.lower()
    for rule in db.list_rules(chat_id):
        pattern = rule["pattern"]
        if rule["is_regex"]:
            try:
                if re.search(pattern, text, re.IGNORECASE):
                    return rule
            except re.error:
                continue
        elif pattern.lower() in lowered:
            return rule
    return None
