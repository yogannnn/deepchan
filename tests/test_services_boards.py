import os

import pytest

from app import create_app
from models import Board, Setting
from models import db as _db
from services.boards import get_boards, get_visible_board_ids


@pytest.fixture
def app_with_boards():
    """Создаёт приложение с изолированной in-memory БД и добавляет две доски."""
    os.environ["DEEPCHAN_TESTING"] = "1"
    app = create_app()
    app.config["TESTING"] = True
    app.config["SERVER_NAME"] = "localhost"
    with app.app_context():
        _db.create_all()
        # Очищаем таблицу перед добавлением, чтобы избежать мусора
        Board.query.delete()
        _db.session.add(Board(short_name="b", name="Бред", description="Тест"))
        _db.session.add(Board(short_name="a", name="Аниме", description="Тест"))
        _db.session.commit()
    yield app
    with app.app_context():
        _db.drop_all()
    os.environ.pop("DEEPCHAN_TESTING", None)


def test_get_boards_returns_all(app_with_boards):
    """Проверяет, что get_boards() возвращает все доски."""
    with app_with_boards.app_context():
        boards = get_boards()
        assert len(boards) == 2
        assert boards[0].short_name == "b"
        assert boards[1].short_name == "a"


def test_get_visible_board_ids(app_with_boards):
    """Проверяет, что get_visible_board_ids() возвращает id всех досок."""
    with app_with_boards.app_context():
        ids = get_visible_board_ids()
        assert len(ids) == 2


def test_boards_filter_list_hook(app_with_boards):
    """Проверяет, что хук boards.filter_list может отфильтровать доски."""
    with app_with_boards.app_context():

        def hide_board_a(boards, **kwargs):
            boards[:] = [b for b in boards if b.short_name != "a"]

        app_with_boards.on("boards.filter_list", hide_board_a)
        boards = get_boards()
        assert len(boards) == 1
        assert boards[0].short_name == "b"
