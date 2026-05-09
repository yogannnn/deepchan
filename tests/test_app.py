import pytest


@pytest.mark.skip(reason="create_app ещё не реализована")
def test_create_app_returns_working_app():
    from app import create_app

    app = create_app()
    assert app is not None
    with app.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200
