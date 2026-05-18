import io

import pytest
from flask import url_for

from models import Board, Post, Thread, db
from services.csrf import generate_csrf_token


def _csrf(app, action="post"):
    token, ts = generate_csrf_token("anonymous", action, app.config["SECRET_KEY"])
    return {"csrf_token": token, "csrf_timestamp": str(ts)}


def test_board_page(app, client):
    resp = client.get("/b/")
    assert resp.status_code == 200
    assert "/b/ - Бред" in resp.data.decode()


def test_board_catalog(app, client):
    resp = client.get("/b/catalog")
    assert resp.status_code == 200
    assert "каталог" in resp.data.decode().lower()


def test_thread_view(app, client):
    with app.app_context():
        board = Board.query.filter_by(short_name="b").first()
        thread = Thread(board_id=board.id)
        db.session.add(thread)
        db.session.flush()
        post = Post(
            thread_id=thread.id, name="Аноним", subject="Тест", comment="Содержимое"
        )
        db.session.add(post)
        db.session.commit()
        tid = thread.id
    resp = client.get(f"/b/thread/{tid}")
    assert resp.status_code == 200
    assert "Тест" in resp.data.decode()
    assert "Содержимое" in resp.data.decode()


def test_thread_with_quote(app, client):
    with app.app_context():
        board = Board.query.filter_by(short_name="b").first()
        thread = Thread(board_id=board.id)
        db.session.add(thread)
        db.session.flush()
        post = Post(thread_id=thread.id, name="Аноним", comment="Цитируемый пост")
        db.session.add(post)
        db.session.commit()
        tid = thread.id
        pid = post.id
    resp = client.get(f"/b/thread/{tid}?reply={pid}")
    assert resp.status_code == 200
    # quote_text в textarea экранирован: >>1 → &gt;&gt;1
    assert f"&gt;&gt;{pid}" in resp.data.decode()


def test_reply_to_thread(app, client):
    with app.app_context():
        board = Board.query.filter_by(short_name="b").first()
        thread = Thread(board_id=board.id)
        db.session.add(thread)
        db.session.flush()
        op = Post(thread_id=thread.id, name="Аноним", subject="Тема", comment="ОП")
        db.session.add(op)
        db.session.commit()
        tid = thread.id

    data = {"name": "Аноним", "comment": "Ответ"}
    data.update(_csrf(app, "post"))
    resp = client.post(f"/b/post?thread_id={tid}", data=data, follow_redirects=True)
    assert resp.status_code == 200
    assert "Ответ" in resp.data.decode()


def test_board_search(app, client):
    with app.app_context():
        board = Board.query.filter_by(short_name="b").first()
        thread = Thread(board_id=board.id)
        db.session.add(thread)
        db.session.flush()
        post = Post(thread_id=thread.id, name="Аноним", comment="уникальный термин")
        post.search_text = "уникальный термин"
        db.session.add(post)
        db.session.commit()
    resp = client.get("/b/search?q=уникальный")
    assert resp.status_code == 200
    assert "уникальный термин" in resp.data.decode()

    resp = client.get("/b/search?q=ничего")
    assert resp.status_code == 200
    assert "Ничего не найдено" in resp.data.decode()


def test_hide_thread(app, client):
    with app.app_context():
        board = Board.query.filter_by(short_name="b").first()
        thread = Thread(board_id=board.id)
        db.session.add(thread)
        db.session.flush()
        op = Post(thread_id=thread.id, name="Аноним", subject="Спрячем", comment="")
        db.session.add(op)
        db.session.commit()
        tid = thread.id
    resp = client.get(f"/b/hide/{tid}", follow_redirects=False)
    assert resp.status_code == 302
    assert "hidden_threads" in resp.headers.get("Set-Cookie", "")


def test_report_post_get(app, client):
    with app.app_context():
        board = Board.query.filter_by(short_name="b").first()
        thread = Thread(board_id=board.id)
        db.session.add(thread)
        db.session.flush()
        post = Post(thread_id=thread.id, name="Аноним", comment="Плохой пост")
        db.session.add(post)
        db.session.commit()
        pid = post.id
    resp = client.get(f"/b/report/{pid}")
    assert resp.status_code == 200
    # Заголовок страницы: "Жалоба на пост #N"
    assert "Жалоба" in resp.data.decode()


def test_report_post_submit(app, client):
    with app.app_context():
        board = Board.query.filter_by(short_name="b").first()
        thread = Thread(board_id=board.id)
        db.session.add(thread)
        db.session.flush()
        post = Post(thread_id=thread.id, name="Аноним", comment="Ещё хуже")
        db.session.add(post)
        db.session.commit()
        pid = post.id

    data = {"reason": "spam", "comment": "реклама"}
    data.update(_csrf(app, "report"))
    resp = client.post(f"/b/report/{pid}", data=data, follow_redirects=True)
    assert resp.status_code == 200
    assert "Ещё хуже" in resp.data.decode()


def test_thread_rss(app, client):
    with app.app_context():
        board = Board.query.filter_by(short_name="b").first()
        thread = Thread(board_id=board.id)
        db.session.add(thread)
        db.session.flush()
        post = Post(
            thread_id=thread.id,
            name="Аноним",
            subject="RSS заголовок",
            comment="RSS контент",
        )
        db.session.add(post)
        db.session.commit()
        tid = thread.id
    resp = client.get(f"/b/thread/{tid}/rss")
    assert resp.status_code == 200
    assert "application/rss+xml" in resp.content_type
    assert "<title>" in resp.data.decode() and "RSS заголовок" in resp.data.decode()
