"""
Сервис для работы с досками.
Единственный источник правды для получения списка досок.
"""
from flask import current_app

from models import Board


def get_visible_board_ids():
    """Возвращает список id досок, видимых после применения хука boards.filter_list."""
    boards = get_boards()
    return [b.id for b in boards]


def get_boards():
    """Возвращает список всех досок, пропущенных через хук boards.filter_list."""
    boards = Board.query.order_by(Board.position).all()
    current_app.emit("boards.filter_list", boards=boards)
    return boards
