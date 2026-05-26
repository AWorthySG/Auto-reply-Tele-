from types import SimpleNamespace
from unittest.mock import AsyncMock

from bot.handlers import auto_reply


def _make_update(text, chat_id=5, user_id=1, username="alice"):
    message = SimpleNamespace(text=text, reply_text=AsyncMock())
    chat = SimpleNamespace(id=chat_id, title="Test", full_name="Test")
    user = SimpleNamespace(id=user_id, username=username)
    return SimpleNamespace(
        effective_message=message,
        effective_chat=chat,
        effective_user=user,
    )


async def test_rule_match_replies_and_logs(fresh_db):
    fresh_db.add_rule(5, "hello", "Hi there!")
    update = _make_update("hello world")
    await auto_reply.on_message(update, context=None)

    update.effective_message.reply_text.assert_awaited_once_with("Hi there!")
    stats = fresh_db.chat_stats(5)
    assert stats["total"] == 1
    assert stats["rule_replies"] == 1


async def test_no_match_no_reply_but_logs(fresh_db):
    update = _make_update("nothing matches")
    await auto_reply.on_message(update, context=None)

    update.effective_message.reply_text.assert_not_awaited()
    stats = fresh_db.chat_stats(5)
    assert stats["total"] == 1
    assert stats["replied"] == 0


async def test_autoreply_disabled_skips_reply(fresh_db):
    fresh_db.add_rule(5, "hello", "Hi there!")
    fresh_db.set_chat_flag(5, "autoreply_enabled", 0)
    update = _make_update("hello world")
    await auto_reply.on_message(update, context=None)

    update.effective_message.reply_text.assert_not_awaited()
    assert fresh_db.chat_stats(5)["total"] == 1
