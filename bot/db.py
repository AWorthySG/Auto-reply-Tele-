import sqlite3
import time
from contextlib import closing
from typing import Optional

from . import config

_conn: Optional[sqlite3.Connection] = None


def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(config.DATABASE_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
    return _conn


def init_db() -> None:
    conn = get_conn()
    with conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS chats (
                chat_id           INTEGER PRIMARY KEY,
                title             TEXT,
                autoreply_enabled INTEGER NOT NULL DEFAULT 1,
                ai_enabled        INTEGER NOT NULL DEFAULT 0,
                system_prompt     TEXT
            );

            CREATE TABLE IF NOT EXISTS rules (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id    INTEGER,            -- NULL = global rule
                pattern    TEXT NOT NULL,
                is_regex   INTEGER NOT NULL DEFAULT 0,
                response   TEXT NOT NULL,
                enabled    INTEGER NOT NULL DEFAULT 1,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id          INTEGER NOT NULL,
                user_id          INTEGER,
                username         TEXT,
                text             TEXT,
                ts               REAL NOT NULL,
                was_auto_replied INTEGER NOT NULL DEFAULT 0,
                reply_type       TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_id);
            CREATE INDEX IF NOT EXISTS idx_rules_chat ON rules(chat_id);
            """
        )


# ---------- chats ----------

def ensure_chat(chat_id: int, title: Optional[str] = None) -> sqlite3.Row:
    conn = get_conn()
    with conn:
        conn.execute(
            "INSERT INTO chats (chat_id, title) VALUES (?, ?) "
            "ON CONFLICT(chat_id) DO UPDATE SET title=COALESCE(excluded.title, chats.title)",
            (chat_id, title),
        )
    with closing(conn.execute("SELECT * FROM chats WHERE chat_id=?", (chat_id,))) as cur:
        return cur.fetchone()


def set_chat_flag(chat_id: int, field: str, value: int) -> None:
    if field not in {"autoreply_enabled", "ai_enabled"}:
        raise ValueError(f"unknown flag {field}")
    ensure_chat(chat_id)
    conn = get_conn()
    with conn:
        conn.execute(f"UPDATE chats SET {field}=? WHERE chat_id=?", (value, chat_id))


def set_system_prompt(chat_id: int, prompt: str) -> None:
    ensure_chat(chat_id)
    conn = get_conn()
    with conn:
        conn.execute("UPDATE chats SET system_prompt=? WHERE chat_id=?", (prompt, chat_id))


# ---------- rules ----------

def add_rule(chat_id: Optional[int], pattern: str, response: str, is_regex: bool = False) -> int:
    conn = get_conn()
    with conn:
        cur = conn.execute(
            "INSERT INTO rules (chat_id, pattern, is_regex, response, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (chat_id, pattern, int(is_regex), response, time.time()),
        )
        return cur.lastrowid


def delete_rule(rule_id: int, chat_id: Optional[int]) -> bool:
    conn = get_conn()
    with conn:
        cur = conn.execute(
            "DELETE FROM rules WHERE id=? AND (chat_id=? OR chat_id IS NULL)",
            (rule_id, chat_id),
        )
        return cur.rowcount > 0


def list_rules(chat_id: int) -> list[sqlite3.Row]:
    conn = get_conn()
    with closing(
        conn.execute(
            "SELECT * FROM rules WHERE (chat_id=? OR chat_id IS NULL) AND enabled=1 "
            "ORDER BY id",
            (chat_id,),
        )
    ) as cur:
        return cur.fetchall()


# ---------- messages / analytics ----------

def log_message(
    chat_id: int,
    user_id: Optional[int],
    username: Optional[str],
    text: Optional[str],
    was_auto_replied: bool = False,
    reply_type: Optional[str] = None,
) -> None:
    conn = get_conn()
    with conn:
        conn.execute(
            "INSERT INTO messages "
            "(chat_id, user_id, username, text, ts, was_auto_replied, reply_type) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (chat_id, user_id, username, text, time.time(), int(was_auto_replied), reply_type),
        )


def chat_stats(chat_id: int) -> dict:
    conn = get_conn()
    with closing(
        conn.execute(
            "SELECT COUNT(*) AS total, "
            "SUM(was_auto_replied) AS replied, "
            "SUM(CASE WHEN reply_type='rule' THEN 1 ELSE 0 END) AS rule_replies, "
            "SUM(CASE WHEN reply_type='ai' THEN 1 ELSE 0 END) AS ai_replies "
            "FROM messages WHERE chat_id=?",
            (chat_id,),
        )
    ) as cur:
        row = cur.fetchone()
    with closing(
        conn.execute(
            "SELECT COALESCE(username, CAST(user_id AS TEXT)) AS who, COUNT(*) AS n "
            "FROM messages WHERE chat_id=? GROUP BY who ORDER BY n DESC LIMIT 5",
            (chat_id,),
        )
    ) as cur:
        top_users = cur.fetchall()
    return {
        "total": row["total"] or 0,
        "replied": row["replied"] or 0,
        "rule_replies": row["rule_replies"] or 0,
        "ai_replies": row["ai_replies"] or 0,
        "top_users": [(r["who"], r["n"]) for r in top_users],
    }


def all_chat_ids() -> list[int]:
    conn = get_conn()
    with closing(conn.execute("SELECT chat_id FROM chats")) as cur:
        return [r["chat_id"] for r in cur.fetchall()]
