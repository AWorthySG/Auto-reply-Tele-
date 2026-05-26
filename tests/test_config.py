from bot.config import _parse_admin_ids


def test_parse_admin_ids_basic():
    assert _parse_admin_ids("111,222") == {111, 222}


def test_parse_admin_ids_whitespace_and_empty():
    assert _parse_admin_ids(" 111 , , 222 ") == {111, 222}


def test_parse_admin_ids_empty_string():
    assert _parse_admin_ids("") == set()
