"""
Сервис для работы с постами.
Единая точка создания и получения постов.
"""
import html
from datetime import datetime, timezone

from flask import current_app, g

from core.exceptions import CaptchaError
from models import Board, Post, PostFile, PostFTS, RadioTrack, Thread, db, hash_password
from services.media import process_file, save_files
from services.security import apply_word_filters
from services.tripcodes import generate_tripcode


def _check_captcha(captcha_answer: str, captcha_token: str) -> None:
    """Проверяет капчу. Выбрасывает CaptchaError при несовпадении."""
    from services.captcha import verify_captcha

    if not verify_captcha(captcha_answer, captcha_token):
        raise CaptchaError("Неверный код капчи")


def create_post(
    board, thread, form, files_data, ip_address, captcha_answer=None, captcha_token=None
):
    """Создаёт пост в указанном треде (или создаёт новый тред, если thread=None).
    Вызывает хуки posts.before_create и posts.after_create.
    Возвращает объект Post.
    """
    # Проверка капчи (если переданы данные)
    if captcha_answer is not None and captcha_token is not None:
        _check_captcha(captcha_answer, captcha_token)

    # Хук перед созданием — плагины могут отклонить пост или модифицировать данные
    current_app.emit(
        "posts.before_create",
        board=board,
        thread=thread,
        form=form,
        ip_address=ip_address,
        identity_hash=getattr(g, "identity", {}).get("id")
        if hasattr(g, "identity")
        else None,
    )

    # Если плагин установил g.captcha_required, принудительно включаем капчу
    if getattr(g, "captcha_required", False):
        current_app.config["SETTINGS"]._cache["CAPTCHA_ENABLED"] = True

    # Применяем фильтры
    filtered_comment = apply_word_filters(form.comment.data)
    filtered_subject = (
        apply_word_filters(form.subject.data) if form.subject.data else None
    )

    # Обработка трипкода
    name_input = form.name.data.strip() if form.name.data else "Аноним"
    display_name = name_input
    tripcode = None
    is_admin = False
    if "#" in name_input:
        parts = name_input.split("#", 1)
        display_name = parts[0] or "Аноним"
        password = parts[1]
        tripcode = generate_tripcode(password, current_app.config["SECRET_KEY"])
        admin_secret = current_app.config["SETTINGS"].admin_trip_secret
        if admin_secret and password == admin_secret:
            is_admin = True

    safe_name = html.escape(display_name) if display_name else "Аноним"
    safe_subject = html.escape(form.subject.data) if form.subject.data else None

    # Сохраняем файлы (защита от None)
    files_to_save = files_data if files_data else []
    saved_files = save_files(files_to_save)

    # Создаём пост
    post = Post(
        thread_id=thread.id,
        name=safe_name,
        tripcode=tripcode,
        is_admin_post=is_admin,
        subject=safe_subject if thread else None,
        comment=filtered_comment,
        sage=form.sage.data,
        password_hash=(
            hash_password(form.password.data) if form.password.data else None
        ),
        ip_address=ip_address,
        identity_hash=getattr(g, "identity", {}).get("id")
        if hasattr(g, "identity")
        else None,
    )
    post.search_text = (post.comment + " " + (post.subject or "")).lower()
    db.session.add(post)
    db.session.flush()

    # Привязываем файлы
    for fn, tn, order, size, sha256, file_type, duration in saved_files:
        pf = PostFile(
            post_id=post.id,
            file_path=fn,
            thumb_path=tn or "",  # гарантируем строку, если None
            file_order=order,
            file_size=size,
            md5_hash=sha256,
            file_type=file_type,
            duration=duration,
        )
        db.session.add(pf)

        # Радио-трек
        if file_type == "audio" and current_app.config["SETTINGS"].radio_enabled:
            if not RadioTrack.query.filter_by(original_hash=sha256).first():
                track = RadioTrack(
                    post_file_id=pf.id,
                    artist="Unknown",
                    title="Untitled",
                    original_hash=sha256,
                    duration=duration,
                    approved=False,
                    file_path=fn,
                )
                db.session.add(track)

    # Обновляем bump
    if not form.sage.data:
        thread.bumped_at = datetime.now(timezone.utc)

    # Полнотекстовый поиск
    fts_entry = PostFTS(
        post_id=post.id,
        board_id=board.id,
        thread_id=thread.id,
        comment=post.comment,
        subject=post.subject or "",
        name=post.name,
    )
    db.session.add(fts_entry)

    db.session.commit()

    # Хук после создания — уведомления, аналитика, etc.
    current_app.emit("posts.after_create", post=post, board=board, thread=thread)

    return post


def get_post(post_id):
    """Возвращает пост по id, пропуская через хук posts.before_render."""
    post = Post.query.get_or_404(post_id)
    current_app.emit("posts.before_render", post=post)
    return post
