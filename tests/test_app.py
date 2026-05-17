def test_create_app_returns_working_app():
    from app import create_app
    from models import Board, db

    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    app.config["TESTING"] = True
    app.config["SERVER_NAME"] = "localhost"

    with app.app_context():
        db.create_all()
        # Создаём таблицу user_preferences, если её нет
        from sqlalchemy import inspect, text

        inspector = inspect(db.engine)
        if "user_preferences" not in inspector.get_table_names():
            db.session.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS user_preferences (
                    identity_hash TEXT PRIMARY KEY,
                    language TEXT DEFAULT 'ru',
                    hidden_boards TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
                )
            )
            db.session.commit()
        if not Board.query.filter_by(short_name="b").first():
            db.session.add(Board(short_name="b", name="Бред", description="Тест"))
            db.session.commit()

    with app.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200
