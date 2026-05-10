import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import Post, Thread, Board
from utils import generate_csrf_token, generate_tripcode


def test_admin_tripcode_shows_badge(client, app):
    with app.app_context():
        board = Board.query.filter_by(short_name="b").first()
        thread = Thread(board_id=board.id)
        db = app.extensions["sqlalchemy"]
        db.session.add(thread)
        db.session.flush()
        db.session.commit()

        # Устанавливаем админский секрет
        app.config["ADMIN_TRIP_SECRET"] = "adminpass"
        app.config["SETTINGS"]._cache["ADMIN_TRIP_SECRET"] = "adminpass"
        token, ts = generate_csrf_token("anonymous", "post", app.config["SECRET_KEY"])

    # Отправляем пост с именем "Админ#adminpass"
    response = client.post(
        "/b/post?thread_id=1",
        data={
            "name": "Админ#adminpass",
            "comment": "Тест трипкода",
            "csrf_token": token,
            "csrf_timestamp": str(ts),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert 'class="admin-badge"' in html or "Adm" in html
