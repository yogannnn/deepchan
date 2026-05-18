import io
from unittest.mock import patch

import pytest
from flask import url_for

from models import Board, Post, Thread, db
from services.csrf import generate_csrf_token


def test_index_returns_200(app, client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Доски" in resp.data.decode()


def test_index_has_board_stats(app, client):
    resp = client.get("/")
    html = resp.data.decode()
    # Проверяем, что есть хотя бы одна доска со статистикой в формате [x|y|+z]
    assert "[0|0|+0]" in html or "[1|" in html


def test_captcha_returns_image(app, client):
    resp = client.get("/captcha")
    assert resp.status_code == 200
    assert resp.mimetype == "image/png"


def test_catalog_global_returns_200(app, client):
    resp = client.get("/catalog")
    assert resp.status_code == 200
    # i18n: может быть "Глобальный каталог" или "Catalog"
    assert "каталог" in resp.data.decode().lower()


def test_catalog_global_filter_by_board(app, client):
    with app.app_context():
        board = Board.query.filter_by(short_name="b").first()
        board_id = board.id
    resp = client.get(f"/catalog?board_id={board_id}")
    assert resp.status_code == 200
    # Проверяем, что в каталоге присутствует имя доски
    assert f"/{board.short_name}/" in resp.data.decode()


def test_catalog_global_with_threads(app, client):
    with app.app_context():
        board = Board.query.filter_by(short_name="b").first()
        # Создадим тред с постом
        thread = Thread(board_id=board.id)
        db.session.add(thread)
        db.session.flush()
        post = Post(
            thread_id=thread.id, name="Аноним", subject="Тестовый тред", comment="Текст"
        )
        db.session.add(post)
        db.session.commit()
        board_id = board.id
    resp = client.get(f"/catalog?board_id={board_id}")
    assert resp.status_code == 200
    assert "Тестовый тред" in resp.data.decode()


def test_global_search_returns_200(app, client):
    resp = client.get("/search")
    assert resp.status_code == 200
    # i18n: может быть "Глобальный поиск" или "Search"
    assert "поиск" in resp.data.decode().lower()


def test_global_search_with_results(app, client):
    with app.app_context():
        board = Board.query.filter_by(short_name="b").first()
        thread = Thread(board_id=board.id)
        db.session.add(thread)
        db.session.flush()
        post = Post(
            thread_id=thread.id, name="Аноним", comment="уникальный поисковый запрос"
        )
        post.search_text = "уникальный поисковый запрос"
        db.session.add(post)
        db.session.commit()
        board_id = board.id
    resp = client.get("/search?q=уникальный+поисковый+запрос")
    assert resp.status_code == 200
    assert "уникальный поисковый запрос" in resp.data.decode()
    resp = client.get(f"/search?q=уникальный&board_id={board_id}")
    assert resp.status_code == 200
    assert "уникальный поисковый запрос" in resp.data.decode()


def test_global_search_no_results(app, client):
    resp = client.get("/search?q=ничегонесуществующий")
    assert resp.status_code == 200
    assert "Ничего не найдено" in resp.data.decode()


def test_bbcode_page(app, client):
    resp = client.get("/bbcode")
    assert resp.status_code == 200
    assert "BB-код" in resp.data.decode() or "bbcode" in resp.data.decode().lower()
