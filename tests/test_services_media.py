import io
import os
import shutil
import tempfile
from io import BytesIO
from unittest.mock import patch

import pytest
from flask import abort, g
from PIL import Image
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import HTTPException

from app import create_app
from core.exceptions import MediaValidationError
from models import Board, Post, Thread
from models import db as _db
from services.media import process_file, save_files


@pytest.fixture
def app_with_media():
    """Создаёт изолированное приложение с временной папкой для загрузок."""
    import os as _os

    _os.environ["DEEPCHAN_TESTING"] = "1"
    app = create_app()
    app.config["TESTING"] = True
    app.config["SERVER_NAME"] = "localhost"

    tmp_upload = tempfile.mkdtemp()
    app.config["UPLOAD_FOLDER"] = tmp_upload
    os.makedirs(os.path.join(tmp_upload, "thumbs"), exist_ok=True)

    with app.app_context():
        _db.create_all()
        board = Board(short_name="b", name="Test", description="Desc")
        thread = Thread(board=board)
        _db.session.add(board)
        _db.session.add(thread)
        _db.session.commit()
        app.board = board
        app.thread = thread

    app.plugin_registry = {}
    app.events = {}

    yield app

    with app.app_context():
        _db.drop_all()
    shutil.rmtree(tmp_upload)
    _os.environ.pop("DEEPCHAN_TESTING", None)


def _make_file(filename="test.jpg", content=None):
    """Создаёт FileStorage-объект с JPEG-изображением в памяти."""
    if content is None:
        img = Image.new("RGB", (10, 10), color="red")
        buf = BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
    else:
        buf = BytesIO(content)
    return FileStorage(stream=buf, filename=filename)


@patch("services.media.get_media_duration", return_value=None)
def test_process_file_image(mock_duration, app_with_media):
    """Проверяет, что process_file сохраняет изображение и возвращает список."""
    with app_with_media.app_context():
        file = _make_file()
        result = process_file(
            file, post=None, board=app_with_media.board, thread=app_with_media.thread
        )
        assert len(result) == 1
        fn, tn, order, size, sha, ftype, dur = result[0]
        assert ftype == "image"
        assert os.path.exists(os.path.join(app_with_media.config["UPLOAD_FOLDER"], fn))


def test_save_files_invalid_extension(app_with_media):
    """Проверяет, что save_files отклоняет неразрешённые расширения."""
    with app_with_media.app_context():
        file = _make_file("test.svg", b"fake svg")
        with pytest.raises(MediaValidationError) as exc:
            save_files([file])
        assert exc.value.status_code == 400


def test_media_before_process_hook(app_with_media):
    """Проверяет, что хук media.before_process может отклонить файл (файл не сохраняется)."""
    with app_with_media.app_context():

        def reject_on_hook(file, post, board, thread, **kwargs):
            g.aborted = True
            abort(400, description="Rejected by hook")

        app_with_media.on("media.before_process", reject_on_hook)
        file = _make_file()
        result = process_file(
            file, post=None, board=app_with_media.board, thread=app_with_media.thread
        )
        assert result == []


def test_media_after_process_hook(app_with_media):
    """Проверяет, что хук media.after_process вызывается после сохранения."""
    with app_with_media.app_context():
        after_called = []

        def on_after(file, post, board, thread, **kwargs):
            after_called.append(file)

        app_with_media.on("media.after_process", on_after)
        file = _make_file()
        process_file(
            file, post=None, board=app_with_media.board, thread=app_with_media.thread
        )
        assert len(after_called) == 1


def test_reject_invalid_extension(app_with_media):
    """Неразрешённое расширение (.svg) должно вызывать MediaValidationError."""
    with app_with_media.app_context():
        file = _make_file("test.svg", b"fake svg")
        with pytest.raises(MediaValidationError) as exc:
            process_file(
                file,
                post=None,
                board=app_with_media.board,
                thread=app_with_media.thread,
            )
        assert exc.value.status_code == 400


def test_reject_corrupt_jpeg(app_with_media):
    """Битый JPEG должен вызывать MediaValidationError."""
    with app_with_media.app_context():
        file = _make_file("broken.jpg", b"this is not a valid jpeg")
        with pytest.raises(MediaValidationError) as exc:
            process_file(
                file,
                post=None,
                board=app_with_media.board,
                thread=app_with_media.thread,
            )
        assert exc.value.status_code == 400


def test_reject_oversized_image(app_with_media):
    """Слишком большая картинка по разрешению вызывает abort 400."""
    with app_with_media.app_context():
        max_dim = app_with_media.config["SETTINGS"].max_image_dimension
        img = Image.new("RGB", (max_dim + 1, max_dim + 1), color="blue")
        buf = BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        buf.name = "big.jpg"
        file = FileStorage(stream=buf, filename="big.jpg")
        with pytest.raises(HTTPException) as exc:
            process_file(
                file,
                post=None,
                board=app_with_media.board,
                thread=app_with_media.thread,
            )
        assert exc.value.code == 400


def test_media_duration_fallback_on_missing_ffprobe(app_with_media, monkeypatch):
    """Если ffprobe отсутствует или падает, get_media_duration возвращает None."""
    from services.media import get_media_duration

    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError),
    )
    result = get_media_duration("nonexistent.mp4")
    assert result is None


def test_process_valid_small_image(app_with_media):
    """Маленькая валидная картинка обрабатывается и сохраняется."""
    with app_with_media.app_context():
        img = Image.new("RGB", (10, 10), color="red")
        buf = BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        buf.name = "small.jpg"
        file = FileStorage(stream=buf, filename="small.jpg")
        result = process_file(
            file, post=None, board=app_with_media.board, thread=app_with_media.thread
        )
        assert len(result) == 1
        fn, tn, order, size, sha, ftype, dur = result[0]
        assert ftype == "image"
        assert os.path.exists(os.path.join(app_with_media.config["UPLOAD_FOLDER"], fn))
