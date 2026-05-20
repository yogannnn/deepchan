import pytest
from flask import url_for

from models import Board, Thread, db
from services.csrf import generate_csrf_token

ADMIN = ("admin", "testpass")


def csrf_for(app, action):
    token, ts = generate_csrf_token("admin", action, app.config["SECRET_KEY"])
    return {"csrf_token": token, "csrf_timestamp": str(ts)}


def test_admin_unauthorized(app, client):
    resp = client.get("/admin/")
    assert resp.status_code == 401


def test_admin_index(app, client):
    app.config["ADMIN_PASSWORD"] = "testpass"
    resp = client.get("/admin/", auth=ADMIN)
    assert resp.status_code == 200
    assert "Админка" in resp.data.decode()


def test_create_board(app, client):
    app.config["ADMIN_PASSWORD"] = "testpass"
    data = {"short_name": "test", "name": "Test board", "description": "desc"}
    data.update(csrf_for(app, "create_board"))
    resp = client.post(
        "/admin/boards/create", data=data, auth=ADMIN, follow_redirects=True
    )
    assert resp.status_code == 200
    resp = client.get("/admin/boards", auth=ADMIN)
    assert b"/test/" in resp.data


def test_delete_board(app, client):
    app.config["ADMIN_PASSWORD"] = "testpass"
    # создаём доску
    data = {"short_name": "todel", "name": "To Delete"}
    data.update(csrf_for(app, "create_board"))
    client.post("/admin/boards/create", data=data, auth=ADMIN, follow_redirects=True)

    with app.app_context():
        b = Board.query.filter_by(short_name="todel").first()
        assert b is not None
        board_id = b.id

    del_data = csrf_for(app, "delete_board")
    resp = client.post(
        f"/admin/boards/delete/{board_id}",
        data=del_data,
        auth=ADMIN,
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        assert Board.query.filter_by(short_name="todel").first() is None


def test_add_ban(app, client):
    app.config["ADMIN_PASSWORD"] = "testpass"
    data = {"ip_pattern": "10.0.0.1", "reason": "test ban"}
    data.update(csrf_for(app, "add_ban"))
    resp = client.post("/admin/bans/add", data=data, auth=ADMIN, follow_redirects=True)
    assert resp.status_code == 200
    resp = client.get("/admin/bans", auth=ADMIN)
    assert b"10.0.0.1" in resp.data


def test_add_word_filter(app, client):
    app.config["ADMIN_PASSWORD"] = "testpass"
    data = {"pattern": "badword", "replacement": "***", "action": "replace"}
    data.update(csrf_for(app, "add_filter"))
    resp = client.post(
        "/admin/filters/add", data=data, auth=ADMIN, follow_redirects=True
    )
    assert resp.status_code == 200
    resp = client.get("/admin/filters", auth=ADMIN)
    assert b"badword" in resp.data


def test_toggle_captcha_setting(app, client):
    app.config["ADMIN_PASSWORD"] = "testpass"
    data = {
        "captcha_enabled": "on",
        "site_lang": "ru",
        "threads_per_page": "10",
        "posts_per_page": "10",
        "max_files": "3",
        "max_content_length": "5",
        "max_image_dimension": "2000",
        "max_video_duration": "60",
        "max_video_size": "20",
        "max_audio_duration": "300",
        "max_audio_size": "15",
        "auto_refresh_interval": "30",
        "rate_limit_seconds": "15",
        "allowed_extensions": "jpg,jpeg,png",
    }
    data.update(csrf_for(app, "save_settings"))
    resp = client.post("/admin/settings", data=data, auth=ADMIN, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        assert app.config["SETTINGS"].captcha_enabled == True


def test_stats_page(app, client):
    app.config["ADMIN_PASSWORD"] = "testpass"
    resp = client.get("/admin/stats", auth=ADMIN)
    assert resp.status_code == 200
    assert "Статистика" in resp.data.decode()


def test_move_thread(app, client):
    app.config["ADMIN_PASSWORD"] = "testpass"
    with app.app_context():
        # используем существующую доску /b/ и создаём новую
        b1 = Board.query.filter_by(short_name="b").first()
        b2 = Board(short_name="movetest", name="Для переноса")
        db.session.add(b2)
        db.session.flush()
        thread = Thread(board_id=b1.id)
        db.session.add(thread)
        db.session.commit()
        tid = thread.id
        b2_id = b2.id

    data = {"new_board_id": b2_id}
    data.update(csrf_for(app, "move_thread"))
    resp = client.post(
        f"/admin/threads/move/{tid}", data=data, auth=ADMIN, follow_redirects=True
    )
    assert resp.status_code == 200
    with app.app_context():
        t = db.session.get(Thread, tid)
        assert t.board_id == b2_id


def test_toggle_pin(app, client):
    app.config["ADMIN_PASSWORD"] = "testpass"
    with app.app_context():
        board = Board.query.filter_by(short_name="b").first()
        thread = Thread(board_id=board.id)
        db.session.add(thread)
        db.session.commit()
        tid = thread.id

    data = csrf_for(app, "toggle_pin")
    resp = client.post(
        f"/admin/threads/toggle_pin/{tid}",
        data=data,
        auth=("admin", "testpass"),
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        t = db.session.get(Thread, tid)
        assert t.is_pinned == True
