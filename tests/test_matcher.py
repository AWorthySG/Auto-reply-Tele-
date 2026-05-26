from bot.services import matcher


def test_keyword_match_case_insensitive(fresh_db):
    fresh_db.add_rule(1, "hello", "Hi!")
    m = matcher.find_match(1, "well HELLO there")
    assert m is not None and m["response"] == "Hi!"


def test_regex_match(fresh_db):
    fresh_db.add_rule(1, r"\bprice\b", "$10", is_regex=True)
    assert matcher.find_match(1, "what's the PRICE?")["response"] == "$10"
    assert matcher.find_match(1, "priceless") is None


def test_no_match_returns_none(fresh_db):
    fresh_db.add_rule(1, "hello", "Hi!")
    assert matcher.find_match(1, "unrelated") is None


def test_empty_text_returns_none(fresh_db):
    fresh_db.add_rule(1, "hello", "Hi!")
    assert matcher.find_match(1, "") is None


def test_global_rule_applies_to_any_chat(fresh_db):
    fresh_db.add_rule(None, "ping", "pong")
    assert matcher.find_match(999, "ping?")["response"] == "pong"


def test_invalid_regex_is_skipped(fresh_db):
    fresh_db.add_rule(1, "([unclosed", "broken", is_regex=True)
    fresh_db.add_rule(1, "ok", "fine")
    assert matcher.find_match(1, "this is ok")["response"] == "fine"
