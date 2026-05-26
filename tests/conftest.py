import os

# Set required env before any bot module is imported.
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:TEST_DUMMY_TOKEN")
os.environ.setdefault("ADMIN_IDS", "111,222")

import pytest  # noqa: E402

from bot import config, db  # noqa: E402


@pytest.fixture
def fresh_db(tmp_path):
    """Point the db layer at an isolated temp SQLite file for each test."""
    db._conn = None
    config.DATABASE_PATH = str(tmp_path / "test.db")
    db.init_db()
    yield db
    if db._conn is not None:
        db._conn.close()
    db._conn = None
