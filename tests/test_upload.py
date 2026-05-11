import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from io import BytesIO
from unittest.mock import patch

from utils import generate_csrf_token


def test_upload_invalid_extension(client, app):
    with app.app_context():
        token, ts = generate_csrf_token("anonymous", "post", app.config["SECRET_KEY"])

    data = {
        "name": "Аноним",
        "subject": "Тест",
        "comment": "Файл",
        "csrf_token": token,
        "csrf_timestamp": str(ts),
        "files": [(BytesIO(b"fake svg"), "test.svg")],
    }
    response = client.post(
        "/b/post", data=data, content_type="multipart/form-data", follow_redirects=True
    )
    assert response.status_code == 400


def test_upload_valid_image(client, app):
    """Загрузка валидного JPEG должна создать пост и вернуть 200."""
    from io import BytesIO

    from PIL import Image

    # Создадим минимальный JPEG в памяти
    img = Image.new("RGB", (10, 10), color="green")
    buf = BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    buf.name = "test.jpg"  # клиент Flask хочет атрибут name

    with app.app_context():
        token, ts = generate_csrf_token("anonymous", "post", app.config["SECRET_KEY"])

    data = {
        "name": "Аноним",
        "subject": "Картинка",
        "comment": "Пост с картинкой",
        "csrf_token": token,
        "csrf_timestamp": str(ts),
        "files": (buf, "test.jpg"),
    }
    response = client.post(
        "/b/post", data=data, content_type="multipart/form-data", follow_redirects=True
    )
    assert response.status_code == 200
    assert "Пост с картинкой" in response.data.decode("utf-8")


@patch("utils.get_media_duration", return_value=30.0)
def test_upload_valid_audio(mock_duration, client, app):
    """Загрузка MP3-заглушки должна создать пост и вернуть 200 (длительность мокирована)."""
    import io

    header = bytes([0xFF, 0xFB, 0x90, 0x00])
    silence = b"\x00" * 417
    frame = header + silence
    buf = io.BytesIO()
    # Генерируем 2000 фреймов, чтобы размер стал заметным
    for _ in range(2000):
        buf.write(frame)
    buf.seek(0)
    buf.name = "test.mp3"

    with app.app_context():
        token, ts = generate_csrf_token("anonymous", "post", app.config["SECRET_KEY"])

    data = {
        "name": "Аноним",
        "subject": "Аудио",
        "comment": "Пост с аудио",
        "csrf_token": token,
        "csrf_timestamp": str(ts),
        "files": (buf, "test.mp3"),
    }
    response = client.post(
        "/b/post", data=data, content_type="multipart/form-data", follow_redirects=True
    )
    assert response.status_code == 200
    assert "Пост с аудио" in response.data.decode("utf-8")
