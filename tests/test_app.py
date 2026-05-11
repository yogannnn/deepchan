def test_create_app_returns_working_app():
    from app import create_app
    from models import Board, db

    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    app.config["TESTING"] = True
    app.config["SERVER_NAME"] = "localhost"

    with app.app_context():
        db.create_all()
        if not Board.query.filter_by(short_name="b").first():
            db.session.add(Board(short_name="b", name="Бред", description="Тест"))
            db.session.commit()

    with app.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200
