import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import Board, Post, Thread


def test_board_rss_returns_xml(client, app):
    """Проверяем, что /b/rss отдаёт XML с правильным Content-Type."""
    with app.app_context():
        board = Board.query.filter_by(short_name="b").first()
        thread = Thread(board_id=board.id)
        db = app.extensions["sqlalchemy"]
        db.session.add(thread)
        db.session.flush()

        post = Post(
            thread_id=thread.id,
            name="Аноним",
            subject="RSS-тест",
            comment="Пост для RSS",
        )
        db.session.add(post)
        db.session.commit()

    response = client.get("/b/rss")
    assert response.status_code == 200
    assert "application/rss+xml" in response.content_type
    assert "<title>/b/ - Бред</title>" in response.data.decode("utf-8")
    assert "RSS-тест" in response.data.decode("utf-8")
