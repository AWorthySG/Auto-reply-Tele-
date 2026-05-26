def test_ensure_chat_upsert(fresh_db):
    row = fresh_db.ensure_chat(5, "First")
    assert row["title"] == "First"
    # Re-ensuring without a title keeps the existing one.
    row2 = fresh_db.ensure_chat(5, None)
    assert row2["title"] == "First"
    assert row2["autoreply_enabled"] == 1
    assert row2["ai_enabled"] == 0


def test_set_chat_flags(fresh_db):
    fresh_db.set_chat_flag(5, "ai_enabled", 1)
    fresh_db.set_chat_flag(5, "autoreply_enabled", 0)
    row = fresh_db.ensure_chat(5)
    assert row["ai_enabled"] == 1
    assert row["autoreply_enabled"] == 0


def test_add_and_delete_rule(fresh_db):
    rid = fresh_db.add_rule(5, "hi", "hello")
    assert any(r["id"] == rid for r in fresh_db.list_rules(5))
    assert fresh_db.delete_rule(rid, 5) is True
    assert all(r["id"] != rid for r in fresh_db.list_rules(5))
    assert fresh_db.delete_rule(rid, 5) is False


def test_delete_rule_wrong_chat(fresh_db):
    rid = fresh_db.add_rule(5, "hi", "hello")
    # A different chat cannot delete a chat-scoped rule.
    assert fresh_db.delete_rule(rid, 6) is False


def test_list_rules_includes_global(fresh_db):
    fresh_db.add_rule(5, "chat", "c")
    fresh_db.add_rule(None, "global", "g")
    patterns = {r["pattern"] for r in fresh_db.list_rules(5)}
    assert patterns == {"chat", "global"}


def test_set_system_prompt(fresh_db):
    fresh_db.set_system_prompt(5, "Be terse.")
    assert fresh_db.ensure_chat(5)["system_prompt"] == "Be terse."


def test_log_message_and_stats(fresh_db):
    fresh_db.log_message(5, 1, "alice", "hi", True, "rule")
    fresh_db.log_message(5, 1, "alice", "hello", True, "ai")
    fresh_db.log_message(5, 2, "bob", "noise", False, None)
    s = fresh_db.chat_stats(5)
    assert s["total"] == 3
    assert s["replied"] == 2
    assert s["rule_replies"] == 1
    assert s["ai_replies"] == 1
    assert s["top_users"][0] == ("alice", 2)
