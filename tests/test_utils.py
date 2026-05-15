import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.captcha import generate_captcha
from services.csrf import generate_csrf_token, verify_csrf_token


def test_generate_captcha(app):
    with app.app_context():
        data, text, token = generate_captcha()
        assert len(text) == 6
        assert text.isdigit()
        assert len(token) > 0


def test_csrf_token_lifecycle():
    user = "anonymous"
    action = "test"
    secret = "super-secret"
    token, ts = generate_csrf_token(user, action, secret)
    assert verify_csrf_token(user, action, token, ts, secret) == True


def test_csrf_expired_token():
    import time

    user = "anonymous"
    action = "test"
    secret = "secret"
    token, ts = generate_csrf_token(user, action, secret)
    old_ts = int(time.time()) - 601  # 10 минут назад
    token_old, _ = generate_csrf_token(user, action, secret, old_ts)
    assert verify_csrf_token(user, action, token_old, old_ts, secret) == False
