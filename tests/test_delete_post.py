import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import Board, Post, Thread, hash_password
from services.csrf import generate_csrf_token


def test_delete_post_wrong_password(client, app):
    """Проверяем, что с неверным паролем пост не удаляется."""
    with app.app_context():
        board = Board.query.filter_by(short_name="b").first()
        thread = Thread(board_id=board.id)
        db = app.extensions["sqlalchemy"]
        db.session.add(thread)
        db.session.flush()

        post = Post(
            thread_id=thread.id,
            name="Аноним",
            comment="Тестовый пост",
            password_hash=hash_password("верныйпароль"),
        )
        db.session.add(post)
        db.session.commit()

        # Сохраняем id, пока сессия жива
        post_id = post.id
        token, ts = generate_csrf_token(
            "anonymous", "delete_post", app.config["SECRET_KEY"]
        )

    # Теперь используем сохранённый post_id
    response = client.post(
        f"/b/delete/{post_id}",
        data={
            "password": "неверныйпароль",
            "csrf_token": token,
            "csrf_timestamp": str(ts),
        },
        follow_redirects=True,
    )

    assert response.status_code == 403

    with app.app_context():
        assert db.session.get(Post, post_id) is not None


def test_delete_post_correct_password(client, app):
    """Проверяем, что с правильным паролем пост удаляется."""
    with app.app_context():
        board = Board.query.filter_by(short_name="b").first()
        thread = Thread(board_id=board.id)
        db = app.extensions["sqlalchemy"]
        db.session.add(thread)
        db.session.flush()

        post = Post(
            thread_id=thread.id,
            name="Аноним",
            comment="Пост для удаления",
            password_hash=hash_password("мойпароль"),
        )
        db.session.add(post)
        db.session.commit()

        post_id = post.id
        token, ts = generate_csrf_token(
            "anonymous", "delete_post", app.config["SECRET_KEY"]
        )

    response = client.post(
        f"/b/delete/{post_id}",
        data={
            "password": "мойпароль",
            "csrf_token": token,
            "csrf_timestamp": str(ts),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        assert db.session.get(Post, post_id) is None
