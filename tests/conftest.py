import pytest
from app import create_app
from models import db as _db, Board


@pytest.fixture(scope="function")
def app():
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

    # Обновляем кеш Settings тестовыми значениями (число, а не строка!)
    if "SETTINGS" in flask_app.config:
        flask_app.config["SETTINGS"]._cache[
            "RATE_LIMIT_SECONDS"
        ] = 0  # вот здесь число!

    with flask_app.app_context():
        _db.create_all()
        if not Board.query.filter_by(short_name="b").first():
            _db.session.add(Board(short_name="b", name="Бред", description="Тест"))
            _db.session.commit()

    yield flask_app

    with flask_app.app_context():
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    return app.test_client()
