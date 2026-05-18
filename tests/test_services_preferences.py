import os

import pytest

from app import create_app
from models import db as _db
from services.preferences import get_preference, set_preference


@pytest.fixture(scope="function")
def app_with_prefs():
    """Создаёт приложение с тестовой in‑memory БД и таблицей user_preferences."""
    os.environ["DEEPCHAN_TESTING"] = "1"
    app = create_app()
    app.config["TESTING"] = True
    app.config["SERVER_NAME"] = "localhost"
    with app.app_context():
        _db.create_all()
        # Создаём таблицу user_preferences вручную
        from sqlalchemy import inspect, text

        inspector = inspect(_db.engine)
        if "user_preferences" not in inspector.get_table_names():
            _db.session.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS user_preferences (
                    identity_hash TEXT PRIMARY KEY,
                    language TEXT DEFAULT 'ru',
                    hidden_boards TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
                )
            )
            _db.session.commit()
    yield app
    with app.app_context():
        _db.drop_all()
    os.environ.pop("DEEPCHAN_TESTING", None)


def test_get_preference_nonexistent(app_with_prefs):
    """Для несуществующего identity возвращается None."""
    with app_with_prefs.app_context():
        assert get_preference("no_such_id", "language") is None


def test_set_and_get_preference(app_with_prefs):
    """Создаём запись и читаем её обратно."""
    with app_with_prefs.app_context():
        set_preference("user1", "language", "en")
        assert get_preference("user1", "language") == "en"


def test_update_preference(app_with_prefs):
    """Обновляем существующую запись."""
    with app_with_prefs.app_context():
        set_preference("user2", "language", "fr")
        set_preference("user2", "language", "de")
        assert get_preference("user2", "language") == "de"
