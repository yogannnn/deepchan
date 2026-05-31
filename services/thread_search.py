"""Сервис полнотекстового поиска похожих тредов (FTS5)."""
from sqlalchemy import text

from models import Thread, db


def index_thread(thread_id, search_text):
    """Добавляет или обновляет запись в thread_fts для треда."""
    db.session.execute(
        text("DELETE FROM thread_fts WHERE rowid = :tid"), {"tid": thread_id}
    )
    db.session.execute(
        text("INSERT INTO thread_fts (rowid, search_text) VALUES (:tid, :text)"),
        {"tid": thread_id, "text": search_text},
    )
    db.session.commit()


def search_similar_threads(thread_id, limit=5):
    """Возвращает похожие треды через FTS5."""
    current = db.session.execute(
        text("SELECT search_text FROM thread_fts WHERE rowid = :tid"),
        {"tid": thread_id},
    ).fetchone()
    if not current or not current[0]:
        return []

    # Формируем запрос из слов длиннее 2 символов
    words = [w for w in current[0].split() if len(w) > 2][:10]
    if not words:
        return []

    fts_query = " OR ".join(f'"{w}"' for w in words)

    rows = db.session.execute(
        text(
            """
            SELECT t.*
            FROM thread t
            JOIN thread_fts fts ON t.id = fts.rowid
            WHERE fts.rowid != :tid
              AND thread_fts MATCH :query
            ORDER BY bm25(thread_fts)
            LIMIT :limit
        """
        ),
        {"tid": thread_id, "query": fts_query, "limit": limit},
    ).fetchall()

    return [Thread.query.get(row.id) for row in rows]
