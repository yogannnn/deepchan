import os

import pytest

from app import create_app
from models import Board, Post, Thread
from models import db as _db
from services.threads import get_board_threads, get_thread


@pytest.fixture
def app_with_threads():
    """Создаёт изолированное приложение с доской /b/ и двумя тредами."""
    os.environ["DEEPCHAN_TESTING"] = "1"
    app = create_app()
    app.config["TESTING"] = True
    app.config["SERVER_NAME"] = "localhost"

    with app.app_context():
        _db.create_all()
        board = Board(short_name="b", name="Бред", description="Тест")
        _db.session.add(board)
        _db.session.flush()

        thread1 = Thread(board_id=board.id)
        _db.session.add(thread1)
        _db.session.flush()
        # Добавляем пост, чтобы тред считался "непустым"
        post = Post(thread_id=thread1.id, name="Test", comment="Hello")
        _db.session.add(post)

        thread2 = Thread(board_id=board.id)
        _db.session.add(thread2)
        _db.session.flush()
        post2 = Post(thread_id=thread2.id, name="Test2", comment="World")
        _db.session.add(post2)

        _db.session.commit()

        app.board_id = board.id
        app.thread1_id = thread1.id
        app.thread2_id = thread2.id

    app.plugin_registry = {}
    app.events = {}

    yield app

    with app.app_context():
        _db.drop_all()
    os.environ.pop("DEEPCHAN_TESTING", None)


def test_get_thread(app_with_threads):
    """Проверяет получение треда по id через сервис."""
    with app_with_threads.app_context():
        thread = get_thread(app_with_threads.thread1_id)
        assert thread.id == app_with_threads.thread1_id
        assert thread.posts.count() == 1


def test_get_board_threads(app_with_threads):
    """Проверяет получение списка тредов доски через сервис."""
    with app_with_threads.app_context():
        threads = get_board_threads(app_with_threads.board_id, only_visible=False)
        assert len(threads) == 2


def test_threads_before_render_hook(app_with_threads):
    """Проверяет, что хук threads.before_render вызывается при получении треда."""
    with app_with_threads.app_context():
        called = []

        def on_before_render(thread, **kwargs):
            called.append(thread.id)

        app_with_threads.on("threads.before_render", on_before_render)
        get_thread(app_with_threads.thread1_id)
        assert app_with_threads.thread1_id in called


def test_threads_list_loaded_hook(app_with_threads):
    """Проверяет, что хук threads.list_loaded вызывается при получении списка."""
    with app_with_threads.app_context():
        called = []

        def on_list_loaded(threads, board_id, **kwargs):
            called.append(len(threads))

        app_with_threads.on("threads.list_loaded", on_list_loaded)
        get_board_threads(app_with_threads.board_id, only_visible=False)
        assert len(called) > 0
        assert called[0] == 2
