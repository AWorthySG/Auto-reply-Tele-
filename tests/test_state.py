import os

from autoreply.state import State


def test_fresh_state_starts_active(tmp_path):
    path = str(tmp_path / "state.json")
    st = State.load(path, now=1000.0)
    assert st.last_self_activity == 1000.0
    assert st.last_reply == {}


def test_is_away_threshold():
    st = State(path="x", last_self_activity=1000.0, last_reply={})
    # 14 minutes -> not away yet (threshold 15)
    assert st.is_away(now=1000.0 + 14 * 60, inactivity_minutes=15) is False
    # exactly 15 minutes -> away
    assert st.is_away(now=1000.0 + 15 * 60, inactivity_minutes=15) is True


def test_touch_activity_resets_away():
    st = State(path="x", last_self_activity=0.0, last_reply={})
    st.touch_activity(now=5000.0)
    assert st.is_away(now=5000.0 + 60, inactivity_minutes=15) is False


def test_cooldown_window():
    st = State(path="x", last_self_activity=0.0, last_reply={})
    st.record_reply(chat_id=42, now=1000.0)
    # 1 hour later, still within 240-min cooldown
    assert st.in_cooldown(42, now=1000.0 + 3600, cooldown_minutes=240) is True
    # 5 hours later, cooldown expired
    assert st.in_cooldown(42, now=1000.0 + 5 * 3600, cooldown_minutes=240) is False
    # unknown chat never in cooldown
    assert st.in_cooldown(99, now=1000.0 + 1, cooldown_minutes=240) is False


def test_save_and_reload_roundtrip(tmp_path):
    path = str(tmp_path / "state.json")
    st = State(path=path, last_self_activity=1234.5, last_reply={7: 800.0})
    st.record_reply(chat_id=9, now=900.0)
    st.save()
    assert os.path.exists(path)

    reloaded = State.load(path, now=0.0)
    assert reloaded.last_self_activity == 1234.5
    assert reloaded.last_reply == {7: 800.0, 9: 900.0}


def test_corrupt_file_falls_back(tmp_path):
    path = str(tmp_path / "state.json")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("not valid json {")
    st = State.load(path, now=2000.0)
    assert st.last_self_activity == 2000.0
    assert st.last_reply == {}
