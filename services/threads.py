from models import Board, PostFTS, Thread, db

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


def get_board_threads(board_id, only_visible=True, limit=42):
    """Возвращает список тредов доски. Если only_visible=True, то только из видимых досок.
    По умолчанию возвращает последние 42 треда, отсортированные по дате."""
    query = Thread.query.filter(Thread.board_id == board_id, Thread.posts.any())
    if only_visible:
        from services.boards import get_visible_board_ids

        query = query.filter(Thread.board_id.in_(get_visible_board_ids()))
    threads = query.order_by(Thread.bumped_at.desc()).limit(limit).all()
    current_app.emit("threads.list_loaded", threads=threads, board_id=board_id)
    return threads


def move_thread(thread_id, new_board_id):
    """Переносит тред на другую доску. Выбрасывает ValueError, если доска не найдена."""
    thread = Thread.query.get_or_404(thread_id)
    board = Board.query.get_or_404(new_board_id)
    old_board_id = thread.board_id
    thread.board_id = new_board_id
    PostFTS.query.filter_by(thread_id=thread.id).update({"board_id": new_board_id})
    db.session.commit()
    current_app.emit(
        "thread.moved",
        thread=thread,
        old_board_id=old_board_id,
        new_board_id=new_board_id,
    )
    return thread
