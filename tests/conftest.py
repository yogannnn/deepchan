import os

import pytest

from app import create_app
from models import Board
from models import db as _db


@pytest.fixture(scope="function")
def app():
    os.environ["DEEPCHAN_TESTING"] = "1"
    flask_app = create_app()
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    flask_app.config["SERVER_NAME"] = "localhost"
    flask_app.config["RATE_LIMIT_SECONDS"] = 0
    flask_app.config["CAPTCHA_ENABLED"] = False
    flask_app.config["ALLOWED_EXTENSIONS"] = [
        "jpg",
        "jpeg",
        "png",
        "gif",
        "webp",
        "mp4",
        "webm",
        "mov",
        "mp3",
        "ogg",
        "flac",
        "wav",
        "m4a",
    ]
    flask_app.config["MAX_CONTENT_LENGTH"] = 10485760
    flask_app.config["MAX_IMAGE_DIMENSION"] = 5000
    flask_app.config["MAX_VIDEO_DURATION"] = 180
    flask_app.config["MAX_VIDEO_SIZE"] = 52428800
    flask_app.config["MAX_AUDIO_DURATION"] = 600
    flask_app.config["MAX_AUDIO_SIZE"] = 31457280
    flask_app.config["WEBP_CONVERT_ENABLED"] = True
    flask_app.config["STEALTH_TRIM"] = True
    flask_app.config["RADIO_ENABLED"] = False
    with flask_app.app_context():
        print("Creating all tables...")
        _db.create_all()
        # Создаём таблицу user_preferences, если её нет (используется плагином language_selector)
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
        print("Tables created.")
        # Убедимся, что таблицы реально есть
        from sqlalchemy import inspect

        inspector = inspect(_db.engine)
        tables = inspector.get_table_names()
        print("Tables in DB:", tables)
        if not Board.query.filter_by(short_name="b").first():
            _db.session.add(Board(short_name="b", name="Бред", description="Тест"))
            _db.session.commit()
            print("Added test board /b/.")
    yield flask_app
    with flask_app.app_context():
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    return app.test_client()
