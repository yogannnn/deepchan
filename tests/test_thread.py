import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import Board, Post, Thread  # 👈 а эти чудо-модели забыли
from services.csrf import generate_csrf_token


def test_open_thread_with_quote(client, app):
    with app.app_context():
        board = Board.query.filter_by(short_name="b").first()
        thread = Thread(board_id=board.id)
        db = app.extensions["sqlalchemy"]
        db.session.add(thread)
        db.session.flush()
        thread_id = thread.id  # 👈 сохраняем id до выхода из контекста

        post1 = Post(
            thread_id=thread_id,
            name="Аноним",
            subject="Тестовый тред",
            comment="Первый пост",
        )
        db.session.add(post1)
        db.session.flush()

        post2 = Post(
            thread_id=thread_id,
            name="Аноним",
            comment=">>1 Второй пост",
        )
        db.session.add(post2)
        db.session.commit()

    response = client.get(f"/b/thread/{thread_id}")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Первый пост" in html
    assert 'href="/b/thread/1#post1"' in html
    assert "&gt;&gt;1" in html
