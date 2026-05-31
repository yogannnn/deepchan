"""Сервис поиска похожих тредов (пока на LIKE, потом переедет на FTS5)."""
from sqlalchemy import text
from models import db, Thread

def index_thread(thread_id, search_text):
    db.session.execute(
        text("DELETE FROM thread_fts WHERE rowid = :tid"),
        {"tid": thread_id}
    )
    db.session.execute(
        text("INSERT INTO thread_fts (rowid, search_text) VALUES (:tid, :text)"),
        {"tid": thread_id, "text": search_text}
    )
    db.session.commit()

def search_similar_threads(thread_id, limit=5):
    current = db.session.execute(
        text("SELECT search_text FROM thread_fts WHERE rowid = :tid"),
        {"tid": thread_id}
    ).fetchone()
    if not current or not current[0]:
        return []

    words = [w for w in current[0].split() if len(w) > 2]
    if not words:
        return []

    # Строим LIKE-условия
    conditions = []
    params = {"tid": thread_id}
    for i, w in enumerate(words[:10]):
        param_name = f"word{i}"
        conditions.append(f"fts.search_text LIKE :{param_name}")
        params[param_name] = f"%{w}%"

    query = "SELECT t.* FROM thread t JOIN thread_fts fts ON t.id = fts.rowid WHERE "
    query += "(" + " OR ".join(conditions) + ")"
    query += " AND fts.rowid != :tid ORDER BY t.bumped_at DESC LIMIT :limit"
    params["limit"] = limit

    rows = db.session.execute(text(query), params).fetchall()
    return [Thread.query.get(row.id) for row in rows]
