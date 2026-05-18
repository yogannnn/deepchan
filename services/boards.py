"""
Сервис для работы с досками.
Единственный источник правды для получения списка досок.
"""
from flask import current_app

from models import Board, Post, Thread, db


def get_visible_board_ids():
    """Возвращает список id досок, видимых после применения хука boards.filter_list."""
    boards = get_boards()
    return [b.id for b in boards]


def get_boards():
    """Возвращает список всех досок, пропущенных через хук boards.filter_list."""
    boards = Board.query.order_by(Board.position).all()
    current_app.emit("boards.filter_list", boards=boards)
    return boards


from datetime import datetime, timedelta, timezone

from sqlalchemy import func


def get_boards_stats(board_ids):
    """Возвращает статистику по доскам: словарь {board_id: {total_threads, total_posts, posts_today}}."""
    if not board_ids:
        return {}
    now = datetime.now(timezone.utc)
    last_24h = now - timedelta(hours=24)

    # 1. Количество тредов
    threads_q = (
        db.session.query(Thread.board_id, func.count(Thread.id))
        .filter(Thread.board_id.in_(board_ids))
        .group_by(Thread.board_id)
        .all()
    )
    threads_dict = dict(threads_q)

    # 2. Всего постов (через связь Thread -> Post)
    posts_q = (
        db.session.query(Thread.board_id, func.count(Post.id))
        .join(Post, Thread.id == Post.thread_id)
        .filter(Thread.board_id.in_(board_ids))
        .group_by(Thread.board_id)
        .all()
    )
    posts_dict = dict(posts_q)

    # 3. Постов за 24 часа
    posts_today_q = (
        db.session.query(Thread.board_id, func.count(Post.id))
        .join(Post, Thread.id == Post.thread_id)
        .filter(Thread.board_id.in_(board_ids), Post.created_at >= last_24h)
        .group_by(Thread.board_id)
        .all()
    )
    posts_today_dict = dict(posts_today_q)

    stats = {}
    for bid in board_ids:
        stats[bid] = {
            "total_threads": threads_dict.get(bid, 0),
            "total_posts": posts_dict.get(bid, 0),
            "posts_today": posts_today_dict.get(bid, 0),
        }
    return stats
