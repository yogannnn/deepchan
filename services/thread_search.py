"""Сервис полнотекстового поиска похожих тредов (FTS5)."""
from sqlalchemy import text
from models import db, Thread, Post

def index_thread(thread_id, search_text):
    """Добавляет или обновляет запись в thread_fts для треда."""
    db.session.execute(
        text("DELETE FROM thread_fts WHERE rowid = :tid"),
        {"tid": thread_id}
    )
    db.session.execute(
        text("INSERT INTO thread_fts (rowid, search_text) VALUES (:tid, :text)"),
        {"tid": thread_id, "text": search_text}
    )
    db.session.commit()

def _build_search_text(thread):
    """Собирает полный текст треда: тема + все посты."""
    op = thread.posts.first()
    text = (op.subject or '') + ' ' + (op.comment or '')
    for post in thread.posts[1:]:
        text += ' ' + (post.comment or '')
    return text

def index_all_threads():
    """Индексирует все существующие треды."""
    threads = Thread.query.all()
    for t in threads:
        index_thread(t.id, _build_search_text(t))

def search_similar_threads(thread_id, limit=5):
    """Возвращает похожие треды через FTS5."""
    current = db.session.execute(
        text("SELECT search_text FROM thread_fts WHERE rowid = :tid"),
        {"tid": thread_id}
    ).fetchone()
    if not current or not current[0]:
        return []

    # Формируем FTS5-запрос: слова длиннее 2 символов, каждое в кавычках
    stopwords = {'это', 'как', 'для', 'что', 'есть', 'быть', 'весь', 'они', 'она', 'оно', 'кто', 'так', 'ещё', 'уже', 'там', 'где', 'всё', 'мож', 'буд'}
    words = [w for w in current[0].split() if len(w) > 2 and w.lower() not in stopwords][:10]
    if not words:
        return []

    fts_query = ' OR '.join(f'"{w}"' for w in words)

    rows = db.session.execute(
        text("""
            SELECT t.*
            FROM thread t
            JOIN thread_fts ON t.id = thread_fts.rowid
            WHERE thread_fts.rowid != :tid
              AND thread_fts MATCH :query
            ORDER BY bm25(thread_fts)
            LIMIT :limit
        """),
        {"tid": thread_id, "query": fts_query, "limit": limit}
    ).fetchall()

    return [Thread.query.get(row.id) for row in rows]
