from autoreply.engine import IncomingMessage, decide_reply
from autoreply.state import State

from .conftest import make_config

NOW = 100_000.0


def away_state() -> State:
    """State where the user has been inactive long enough to be 'away'."""
    return State(path="x", last_self_activity=NOW - 3600, last_reply={})


def private_msg(text="hello", **kw) -> IncomingMessage:
    return IncomingMessage(chat_id=1, text=text, is_private=True, is_group=False, sender_id=1, **kw)


def group_msg(text="hello", **kw) -> IncomingMessage:
    return IncomingMessage(chat_id=-100, text=text, is_private=False, is_group=True, sender_id=5, **kw)


def test_private_default_reply_when_away():
    cfg = make_config()
    assert decide_reply(private_msg("just saying hi"), away_state(), cfg, NOW) == "DEFAULT_REPLY"


def test_private_keyword_reply_when_away():
    cfg = make_config()
    assert decide_reply(private_msg("what's the price?"), away_state(), cfg, NOW) == "PRICE_REPLY"


def test_no_reply_when_user_is_active():
    cfg = make_config()
    active = State(path="x", last_self_activity=NOW - 60, last_reply={})  # active 1 min ago
    assert decide_reply(private_msg("hi"), active, cfg, NOW) is None


def test_away_disabled_replies_regardless_of_activity():
    cfg = make_config(away={"enabled": False})
    active = State(path="x", last_self_activity=NOW, last_reply={})
    assert decide_reply(private_msg("hi"), active, cfg, NOW) == "DEFAULT_REPLY"


def test_empty_text_is_ignored():
    cfg = make_config()
    assert decide_reply(private_msg("   "), away_state(), cfg, NOW) is None


def test_group_requires_mention_by_default():
    cfg = make_config()
    assert decide_reply(group_msg("hi everyone"), away_state(), cfg, NOW) is None


def test_group_replies_when_mentioned():
    cfg = make_config()
    assert decide_reply(group_msg("hey @me price?", is_mention=True), away_state(), cfg, NOW) == "PRICE_REPLY"


def test_group_replies_when_reply_to_me():
    cfg = make_config()
    assert decide_reply(group_msg("thanks!", is_reply_to_me=True), away_state(), cfg, NOW) == "DEFAULT_REPLY"


def test_group_all_messages_when_mention_disabled():
    cfg = make_config(groups={"only_when_mentioned": False})
    assert decide_reply(group_msg("random chatter"), away_state(), cfg, NOW) == "DEFAULT_REPLY"


def test_groups_disabled():
    cfg = make_config(groups={"enabled": False})
    assert decide_reply(group_msg("hi", is_mention=True), away_state(), cfg, NOW) is None


def test_private_disabled():
    cfg = make_config(private_chats={"enabled": False})
    assert decide_reply(private_msg("hi"), away_state(), cfg, NOW) is None


def test_cooldown_blocks_second_reply():
    cfg = make_config()
    st = away_state()
    st.record_reply(chat_id=1, now=NOW - 60)  # replied 1 min ago, cooldown 240 min
    assert decide_reply(private_msg("hi again"), st, cfg, NOW) is None


def test_reply_allowed_after_cooldown():
    cfg = make_config()
    st = away_state()
    st.record_reply(chat_id=1, now=NOW - 5 * 3600)  # 5h ago > 240 min
    assert decide_reply(private_msg("hi again"), st, cfg, NOW) == "DEFAULT_REPLY"


def test_ignore_user_id():
    cfg = make_config(ignore={"user_ids": [1]})
    assert decide_reply(private_msg("price?"), away_state(), cfg, NOW) is None


def test_ignore_chat_id():
    cfg = make_config(ignore={"chat_ids": [-100]})
    assert decide_reply(group_msg("price?", is_mention=True), away_state(), cfg, NOW) is None


def test_signature_appended():
    cfg = make_config(signature="\n-- bot")
    assert decide_reply(private_msg("hi"), away_state(), cfg, NOW) == "DEFAULT_REPLY\n-- bot"


def test_channel_or_unknown_never_replies():
    cfg = make_config()
    msg = IncomingMessage(chat_id=7, text="hi", is_private=False, is_group=False)
    assert decide_reply(msg, away_state(), cfg, NOW) is None
