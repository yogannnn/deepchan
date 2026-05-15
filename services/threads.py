"""
Сервис для работы с тредами.
Единая точка получения тредов и списков тредов.
"""
from flask import current_app

from models import Thread


def get_thread(thread_id):
    """Возвращает тред по id, пропуская через хук threads.before_render."""
    thread = Thread.query.get_or_404(thread_id)
    current_app.emit("threads.before_render", thread=thread)
    return thread


def get_board_threads(board_id, only_visible=True):
    """Возвращает список тредов доски. Если only_visible=True, то только из видимых досок."""
    query = Thread.query.filter(Thread.board_id == board_id, Thread.posts.any())
    if only_visible:
        from services.boards import get_visible_board_ids

        query = query.filter(Thread.board_id.in_(get_visible_board_ids()))
    threads = query.order_by(Thread.is_pinned.desc(), Thread.bumped_at.desc()).all()
    current_app.emit("threads.list_loaded", threads=threads, board_id=board_id)
    return threads
