"""Сервис для получения общей статистики без вызова хуков."""
from sqlalchemy import func

from models import Board, Post, PostFile, Thread, db


def get_global_stats():
    """Возвращает словарь с количеством досок, тредов, постов и файлов."""
    boards = db.session.query(func.count(Board.id)).scalar()
    threads = db.session.query(func.count(Thread.id)).scalar()
    posts = db.session.query(func.count(Post.id)).scalar()
    files = db.session.query(func.count(PostFile.id)).scalar()
    return {
        "boards": boards,
        "threads": threads,
        "posts": posts,
        "files": files,
    }
