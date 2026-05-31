from sqlalchemy import inspect, text

from models import Board, db


def run_migrations(app):
    with app.app_context():
        db.create_all()
        inspector = inspect(db.engine)
        # Создаём виртуальную таблицу для полнотекстового поиска по тредам
        if not inspector.has_table("thread_fts"):
            db.session.execute(
                text(
                    """
                CREATE VIRTUAL TABLE IF NOT EXISTS thread_fts
                USING fts5(search_text, content_rowid='thread_id')
            """
                )
            )
            db.session.commit()

        if not inspector.has_table("board"):
            db.create_all()

        columns = (
            [c["name"] for c in inspector.get_columns("board")]
            if inspector.has_table("board")
            else []
        )
        if "position" not in columns:
            db.session.execute(
                text("ALTER TABLE board ADD COLUMN position INTEGER DEFAULT 0")
            )
            db.session.commit()

        if not Board.query.filter_by(short_name="b").first():
            db.session.add(Board(short_name="b", name="Бред", description="Бред"))
            db.session.commit()
