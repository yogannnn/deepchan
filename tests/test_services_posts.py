import os

import pytest

from app import create_app
from forms import PostForm
from models import Board, Post, Setting, Thread
from models import db as _db
from services.posts import create_post, get_post


@pytest.fixture
def app_with_data():
    """Создаёт изолированное приложение с доской /b/ и тредом."""
    os.environ["DEEPCHAN_TESTING"] = "1"
    app = create_app()
    app.config["TESTING"] = True
    app.config["SERVER_NAME"] = "localhost"

    with app.app_context():
        _db.create_all()
        board = Board(short_name="b", name="Бред", description="Тест")
        thread = Thread(board=board)
        _db.session.add(board)
        _db.session.add(thread)
        _db.session.commit()
        # Сохраняем id, а не объекты, чтобы избежать DetachedInstanceError
        app.board_id = board.id
        app.thread_id = thread.id

    # Удаляем плагины, чтобы они не влияли на тесты
    app.plugin_registry = {}
    app.events = {}

    yield app

    with app.app_context():
        _db.drop_all()
    os.environ.pop("DEEPCHAN_TESTING", None)


def _get_board_thread(app):
    """Возвращает свежие объекты Board и Thread из текущей сессии."""
    board = _db.session.get(Board, app.board_id)
    thread = _db.session.get(Thread, app.thread_id)
    return board, thread


def test_create_post(app_with_data):
    """Проверяет создание нового поста через сервис."""
    with app_with_data.app_context():
        board, thread = _get_board_thread(app_with_data)
        form = PostForm()
        form.name.data = "Тест"
        form.subject.data = "Тестовая тема"
        form.comment.data = "Тестовый комментарий"
        form.sage.data = False

        post = create_post(
            board=board, thread=thread, form=form, files_data=[], ip_address="127.0.0.1"
        )

        assert post.id is not None
        assert post.name == "Тест"
        assert post.comment == "Тестовый комментарий"


def test_get_post(app_with_data):
    """Проверяет получение поста через сервис."""
    with app_with_data.app_context():
        board, thread = _get_board_thread(app_with_data)
        form = PostForm()
        form.name.data = "Тест2"
        form.subject.data = "Тема2"
        form.comment.data = "Комментарий2"
        form.sage.data = False

        post = create_post(
            board=board, thread=thread, form=form, files_data=[], ip_address="127.0.0.1"
        )
        fetched = get_post(post.id)
        assert fetched.id == post.id
        assert fetched.comment == "Комментарий2"


def test_posts_before_create_hook(app_with_data):
    """Проверяет, что хук posts.before_create вызывается и может модифицировать данные."""
    with app_with_data.app_context():
        board, thread = _get_board_thread(app_with_data)

        def modify_comment(board, thread, form, ip_address, **kwargs):
            form.comment.data = "Модифицированный комментарий"

        app_with_data.on("posts.before_create", modify_comment)

        form = PostForm()
        form.name.data = "Тест3"
        form.subject.data = "Тема3"
        form.comment.data = "Оригинальный комментарий"
        form.sage.data = False

        post = create_post(
            board=board, thread=thread, form=form, files_data=[], ip_address="127.0.0.1"
        )
        assert post.comment == "Модифицированный комментарий"


def test_posts_after_create_hook(app_with_data):
    """Проверяет, что хук posts.after_create вызывается."""
    with app_with_data.app_context():
        board, thread = _get_board_thread(app_with_data)
        created_posts = []

        def track_created(post, board, thread, **kwargs):
            created_posts.append(post)

        app_with_data.on("posts.after_create", track_created)

        form = PostForm()
        form.name.data = "Тест4"
        form.subject.data = "Тема4"
        form.comment.data = "Комментарий4"
        form.sage.data = False

        post = create_post(
            board=board, thread=thread, form=form, files_data=[], ip_address="127.0.0.1"
        )
        assert len(created_posts) == 1
        assert created_posts[0].id == post.id
