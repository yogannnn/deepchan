import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.csrf import generate_csrf_token


def test_non_admin_cannot_approve_track(client, app):
    with app.app_context():
        token, ts = generate_csrf_token(
            "anonymous", "approve_radio", app.config["SECRET_KEY"]
        )

    # Пытаемся одобрить несуществующий трек без авторизации
    response = client.post(
        "/admin/radio/approve/999",
        data={
            "csrf_token": token,
            "csrf_timestamp": str(ts),
        },
        follow_redirects=True,
    )

    assert response.status_code == 401
