import pytest
from app import app as flask_app
from models import db, Board


@pytest.fixture(scope="function")
def app():
    flask_app.config["TESTING"] = True
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    flask_app.config["WTF_CSRF_ENABLED"] = False
    flask_app.config["CAPTCHA_ENABLED"] = False
    flask_app.config["SERVER_NAME"] = "localhost"
    flask_app.config["RATE_LIMIT_SECONDS"] = 0  # 👈 отключаем лимит
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
