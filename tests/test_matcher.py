from autoreply.matcher import match_rule_reply

from .conftest import make_config


def test_first_matching_rule_wins():
    cfg = make_config()
    assert match_rule_reply("What is the price?", cfg) == "PRICE_REPLY"
    assert match_rule_reply("Can we set up a meeting?", cfg) == "MEETING_REPLY"


def test_match_is_case_insensitive():
    cfg = make_config()
    assert match_rule_reply("PRICE please", cfg) == "PRICE_REPLY"


def test_substring_match():
    cfg = make_config()
    # "cost" appears inside "costs"
    assert match_rule_reply("how much does it costs", cfg) == "PRICE_REPLY"


def test_falls_back_to_default():
    cfg = make_config()
    assert match_rule_reply("hello there", cfg) == "DEFAULT_REPLY"


def test_no_default_returns_none():
    cfg = make_config(default_reply=None)
    assert match_rule_reply("hello there", cfg) is None


def test_rule_precedence_when_multiple_match():
    cfg = make_config(
        rules=[
            {"keywords": ["meeting"], "reply": "FIRST"},
            {"keywords": ["price"], "reply": "SECOND"},
        ]
    )
    # message contains both keywords; the earlier rule wins
    assert match_rule_reply("meeting about price", cfg) == "FIRST"
