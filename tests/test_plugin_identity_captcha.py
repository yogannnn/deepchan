import os

import pytest
from sqlalchemy import inspect, text

from app import create_app
from models import Board, Post, Setting, Thread
from models import db as _db
from services.trust import get_trust_score


@pytest.fixture(scope="function")
def app_with_identity():
    """Создаёт приложение с in‑memory БД, создаёт user_preferences и отключает transport_identity."""
    os.environ["DEEPCHAN_TESTING"] = "1"
    app = create_app()
    app.config["TESTING"] = True
    app.config["SERVER_NAME"] = "localhost"

    with app.app_context():
        _db.create_all()

        # Создаём таблицу user_preferences (нужна для language_selector)
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

        # Отключаем плагин transport_identity через настройку БД
        setting = Setting.query.filter_by(
            key="plugin_transport_identity_enabled"
        ).first()
        if not setting:
            setting = Setting(key="plugin_transport_identity_enabled", value="false")
            _db.session.add(setting)
        else:
            setting.value = "false"
        _db.session.commit()

        # Удаляем все before_request-функции, принадлежащие transport_identity
        to_remove = []
        for func in app.before_request_funcs.get(None, []):
            module = getattr(func, "__module__", "")
            if "transport_identity" in module:
                to_remove.append(func)
        for func in to_remove:
            app.before_request_funcs[None].remove(func)

        # Создаём базовые объекты для тестов (доска и тред)
        board = Board(short_name="b", name="test")
        thread = Thread(board=board)
        _db.session.add(board)
        _db.session.add(thread)
        _db.session.commit()
        app.board_id = board.id
        app.thread_id = thread.id

    yield app

    with app.app_context():
        _db.drop_all()
    os.environ.pop("DEEPCHAN_TESTING", None)


def test_low_trust_forces_captcha(app_with_identity):
    """Для identity с низким trust_score капча становится обязательной."""
    with app_with_identity.app_context():
        from flask import g

        g.identity = {"id": "low_trust_user", "transport": "i2p"}
        for func in app_with_identity.before_request_funcs.get(None, []):
            with app_with_identity.test_request_context("/"):
                func()
        assert g.get("captcha_required") == True


def test_high_trust_no_captcha(app_with_identity):
    """Для identity с высоким trust_score капча не форсируется."""
    identity = "high_trust_user"
    with app_with_identity.app_context():
        thread = _db.session.get(Thread, app_with_identity.thread_id)
        for i in range(20):
            post = Post(
                thread_id=thread.id,
                name="test",
                comment=f"post {i}",
                identity_hash=identity,
            )
            _db.session.add(post)
        _db.session.commit()

        score = get_trust_score(identity)
        assert score >= 70, f"Expected high trust, got {score}"

        from flask import g

        g.identity = {"id": identity, "transport": "i2p"}
        for func in app_with_identity.before_request_funcs.get(None, []):
            with app_with_identity.test_request_context("/"):
                func()
        assert not g.get("captcha_required")
