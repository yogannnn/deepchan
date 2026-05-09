import time
import random


class ParanoidMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        def custom_start_response(status, headers, exc_info=None):
            new_headers = [
                (k, v) for k, v in headers if k not in ("Server", "X-Powered-By")
            ]
            return start_response(status, new_headers, exc_info)

        time.sleep(random.uniform(0.005, 0.05))
        return self.app(environ, custom_start_response)


from flask import request, render_template


def inject_csrf_token(app):
    @app.context_processor
    def _inject():
        from utils import generate_csrf_token

        def make_csrf_token(action):
            user_id = (
                request.authorization.username if request.authorization else "anonymous"
            )
            token, timestamp = generate_csrf_token(
                user_id, action, app.config["SECRET_KEY"]
            )
            return {"token": token, "timestamp": timestamp}

        return dict(csrf_token=make_csrf_token)


def check_board_closed(app):
    @app.before_request
    def _check():
        if app.config.get("BOARD_CLOSED", False):
            if request.path.startswith("/admin") or request.path.startswith("/static"):
                return
            if request.endpoint != "board_closed":
                return render_template("board_closed.html"), 503
