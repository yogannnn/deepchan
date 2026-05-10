from flask import Flask, render_template, request
from flask_compress import Compress
from core.middleware import ParanoidMiddleware, inject_csrf_token, check_board_closed
from config import Config
from models import db, Setting, RadioTrack, Post, Board, Thread, PostFTS
from utils import process_comment
from sqlalchemy import inspect, text
import os
import logging
from logging.handlers import RotatingFileHandler


def create_app():
    app = Flask(__name__)
    Compress(app)
    app.config.from_object(Config)
    db.init_app(app)
    app.secret_key = app.config["SECRET_KEY"]
    # Инициализируем настройки (типизированная обёртка)
    from core.settings import Settings

    settings = Settings(app)
    app.config["SETTINGS"] = settings
    app.jinja_env.filters["process_comment"] = process_comment

    if not app.debug:
        handler = RotatingFileHandler("logs/board.log", maxBytes=10000, backupCount=3)
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "thumbs"), exist_ok=True)

    # Регистрируем blueprints
    from blueprints.main import main_bp
    from blueprints.board import board_bp
    from blueprints.admin import admin_bp
    from blueprints.radio import radio_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(board_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(radio_bp)

    # Внедряем middleware
    inject_csrf_token(app)
    check_board_closed(app)
    app.wsgi_app = ParanoidMiddleware(app.wsgi_app)

    @app.route("/closed")
    def board_closed():
        return render_template("board_closed.html")

    @app.after_request
    def add_cache_headers(response):
        if request.path.startswith("/static"):
            response.cache_control.no_cache = False
            response.cache_control.no_store = False
            if request.path.endswith(".css") or "/fonts/" in request.path:
                response.cache_control.max_age = 31536000
                response.cache_control.immutable = True
                response.cache_control.public = True
            elif request.path.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                response.cache_control.max_age = 86400
                response.cache_control.public = True
            else:
                response.cache_control.max_age = 3600
        else:
            response.cache_control.no_cache = True
            response.cache_control.no_store = True
        return response

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.errorhandler(400)
    def bad_request(e):
        return render_template("errors/400.html", description=e.description), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html", description=e.description), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("errors/404.html", description=e.description), 404

    @app.errorhandler(429)
    def too_many_requests(e):
        return render_template("errors/429.html", description=e.description), 429

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("errors/500.html", description=e.description), 500

    return app


if __name__ == "__main__":
    app = create_app()

    with app.app_context():
        # Применяем все миграции (таблицы, колонки, дефолтная доска /b/)
        from migrate import run_migrations

        run_migrations(app)

        # Загружаем настройки из БД (старый метод, пока не перешли на Settings полностью)

    # Определяем режим запуска
    deploy_mode = app.config.get("DEPLOY_MODE", "production")

    if deploy_mode == "development":
        print("🚀 Запуск через Flask development server на http://0.0.0.0:5000")
        app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
    else:
        from gevent.pywsgi import WSGIServer

        print("🚀 Запуск через Gevent (стриминг) на http://0.0.0.0:5000")
        http_server = WSGIServer(("0.0.0.0", 5000), app)
        http_server.serve_forever()
