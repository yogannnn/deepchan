from models import db, Setting, RadioTrack, PostFTS, Post, Board
from sqlalchemy import inspect, text


def run_migrations(app):
    with app.app_context():
        db.create_all()

        if not inspect(db.engine).has_table("setting"):
            Setting.__table__.create(db.engine)
        if not inspect(db.engine).has_table("radio_track"):
            RadioTrack.__table__.create(db.engine)
        if not inspect(db.engine).has_table("post_fts"):
            PostFTS.__table__.create(db.engine)

        with db.engine.connect() as conn:
            for table, col, col_type in [
                ("post", "search_text", "TEXT"),
                ("post_file", "md5_hash", "VARCHAR(32)"),
                ("post_file", "file_size", "INTEGER DEFAULT 0"),
                ("post", "ip_address", "VARCHAR(45)"),
                ("post_file", "file_type", 'VARCHAR(20) DEFAULT "image"'),
                ("post_file", "duration", "FLOAT"),
                ("board", "position", "INTEGER DEFAULT 0"),
                ("post", "tripcode", "VARCHAR(32)"),
                ("post", "is_admin_post", "BOOLEAN DEFAULT 0"),
            ]:
                table_name = table.split(".")[0]
                res = conn.execute(text(f"PRAGMA table_info({table_name})"))
                cols = [row[1] for row in res]
                if col not in cols:
                    conn.execute(
                        text(f"ALTER TABLE {table_name} ADD COLUMN {col} {col_type}")
                    )
            conn.commit()

        for post in Post.query.all():
            if not post.search_text:
                post.search_text = (post.comment + " " + (post.subject or "")).lower()
        db.session.commit()

        if not Board.query.filter_by(short_name="b").first():
            b = Board(short_name="b", name="Бред", description="Общий раздел")
            db.session.add(b)
            db.session.commit()
