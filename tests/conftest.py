import pytest
from app import create_app
from models import db, Board


@pytest.fixture(scope="function")
def app():
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    flask_app.config["WTF_CSRF_ENABLED"] = False
    flask_app.config["CAPTCHA_ENABLED"] = False
    flask_app.config["SERVER_NAME"] = "localhost"
    # Отключаем rate-limit в тестах, обновляя кеш Settings
    if "SETTINGS" in flask_app.config:
        flask_app.config["SETTINGS"]._cache["RATE_LIMIT_SECONDS"] = "0"
    flask_app.config["RATE_LIMIT_SECONDS"] = 0
    with flask_app.app_context():
        db.create_all()
        if not Board.query.filter_by(short_name="b").first():
            db.session.add(Board(short_name="b", name="Бред", description="Тест"))
            db.session.commit()
    yield flask_app
    with flask_app.app_context():
        db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    return app.test_client()
