import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import Board, Post, Thread
from utils import generate_csrf_token


def test_create_thread(client, app):
    with app.app_context():
        token, ts = generate_csrf_token("anonymous", "post", app.config["SECRET_KEY"])

    response = client.post(
        "/b/post",
        data={
            "name": "Тестовый",
            "subject": "Привет, pytest!",
            "comment": "Этот пост создан автоматически.",
            "csrf_token": token,
            "csrf_timestamp": str(ts),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Этот пост создан автоматически." in response.data.decode("utf-8")


def test_create_thread_without_subject(client, app):
    with app.app_context():
        token, ts = generate_csrf_token("anonymous", "post", app.config["SECRET_KEY"])

    response = client.post(
        "/b/post",
        data={
            "name": "Аноним",
            "subject": "",  # ПУСТАЯ ТЕМА
            "comment": "Пост без темы",
            "csrf_token": token,
            "csrf_timestamp": str(ts),
        },
        follow_redirects=True,
    )

    assert response.status_code == 400
    assert "Тема обязательна" in response.data.decode("utf-8")
