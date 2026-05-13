import importlib
import json
import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, render_template, request
from flask_compress import Compress

from config import Config
from core.i18n import t
from core.middleware import ParanoidMiddleware, check_board_closed, inject_csrf_token
from core.settings import Settings
from migrate import run_migrations
from models import Board, Post, PostFTS, RadioTrack, Setting, Thread, db
from utils import process_comment


def create_app():
    app = Flask(__name__)
    Compress(app)
    app.config.from_object(Config)
    db.init_app(app)
    app.secret_key = app.config["SECRET_KEY"]
    app.jinja_env.filters["process_comment"] = process_comment
    app.jinja_env.globals["t"] = t

    settings = Settings(app)
    with app.app_context():
        settings.load()
    app.config["SETTINGS"] = settings

    # Инициализируем систему событий
    app.events = {}

    def on(event_name, callback):
        if event_name not in app.events:
            app.events[event_name] = []
        app.events[event_name].append(callback)

    def emit(event_name, **kwargs):
        results = []
        for callback in app.events.get(event_name, []):
            try:
                result = callback(**kwargs)
                if result is not None:
                    results.append(result)
            except Exception as e:
                app.logger.error(
                    f"Hook {event_name} error in {callback.__qualname__}: {e}"
                )
        return results

    app.on = on
    app.emit = emit

    # Загружаем плагины из папки plugins/
    plugins_dir = os.path.join(app.root_path, "plugins")
    if os.path.isdir(plugins_dir):
        for plugin_name in os.listdir(plugins_dir):
            plugin_path = os.path.join(plugins_dir, plugin_name)
            init_file = os.path.join(plugin_path, "__init__.py")
            if os.path.isfile(init_file):
                try:
                    # Проверяем манифест
                    manifest_path = os.path.join(plugin_path, "plugin.json")
                    if os.path.isfile(manifest_path):
                        with open(manifest_path) as f:
                            manifest = json.load(f)
                        app.logger.info(
                            f'Loading plugin: {manifest.get("name", plugin_name)}'
                        )

                    # Загружаем модуль и вызываем init_app
                    spec = importlib.util.spec_from_file_location(
                        f"plugins.{plugin_name}", init_file
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    if hasattr(module, "init_app"):
                        module.init_app(app)
                except Exception as e:
                    app.logger.error(f"Failed to load plugin {plugin_name}: {e}")

    # Отправляем сигнал о старте
    app.emit("core.started", app=app)

    if not app.debug:
        handler = RotatingFileHandler("logs/board.log", maxBytes=10000, backupCount=3)
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "thumbs"), exist_ok=True)

    # Регистрируем blueprints
    from blueprints.admin import admin_bp
    from blueprints.board import board_bp
    from blueprints.main import main_bp
    from blueprints.radio import radio_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(board_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(radio_bp)

    # Внедряем middleware
    inject_csrf_token(app)
    check_board_closed(app)

    @app.context_processor
    def inject_widgets():
        """Собирает виджеты для шапки и подвала."""
        header_widgets = app.emit("ui.header_rendering", request=request)
        footer_widgets = app.emit("ui.footer_rendering", request=request)
        return dict(header_widgets=header_widgets, footer_widgets=footer_widgets)

    app.wsgi_app = ParanoidMiddleware(app.wsgi_app)

    @app.route("/closed")
    def board_closed():
        return render_template("board_closed.html")

    @app.after_request
    def add_cache_headers(response):
        app.emit("http.after_request", request=request, response=response)
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
        response.headers[
            "Content-Security-Policy"
        ] = "default-src 'none'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
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
    run_migrations(app)

    with app.app_context():
        settings = Settings(app)
    with app.app_context():
        settings.load()
        settings.load()
        app.config["SETTINGS"] = settings

    # Инициализируем систему событий
    app.events = {}

    def on(event_name, callback):
        if event_name not in app.events:
            app.events[event_name] = []
        app.events[event_name].append(callback)

    def emit(event_name, **kwargs):
        results = []
        for callback in app.events.get(event_name, []):
            try:
                result = callback(**kwargs)
                if result is not None:
                    results.append(result)
            except Exception as e:
                app.logger.error(
                    f"Hook {event_name} error in {callback.__qualname__}: {e}"
                )
        return results

    app.on = on
    app.emit = emit

    # Загружаем плагины из папки plugins/
    plugins_dir = os.path.join(app.root_path, "plugins")
    if os.path.isdir(plugins_dir):
        for plugin_name in os.listdir(plugins_dir):
            plugin_path = os.path.join(plugins_dir, plugin_name)
            init_file = os.path.join(plugin_path, "__init__.py")
            if os.path.isfile(init_file):
                try:
                    # Проверяем манифест
                    manifest_path = os.path.join(plugin_path, "plugin.json")
                    if os.path.isfile(manifest_path):
                        with open(manifest_path) as f:
                            manifest = json.load(f)
                        app.logger.info(
                            f'Loading plugin: {manifest.get("name", plugin_name)}'
                        )

                    # Загружаем модуль и вызываем init_app
                    spec = importlib.util.spec_from_file_location(
                        f"plugins.{plugin_name}", init_file
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    if hasattr(module, "init_app"):
                        module.init_app(app)
                except Exception as e:
                    app.logger.error(f"Failed to load plugin {plugin_name}: {e}")

    # Отправляем сигнал о старте
    app.emit("core.started", app=app)

    deploy_mode = app.config["SETTINGS"].deploy_mode

    if deploy_mode == "development":
        print("🚀 Запуск через Flask development server на http://0.0.0.0:5000")
        app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
    else:
        from gevent.pywsgi import WSGIServer

        print("🚀 Запуск через Gevent (стриминг) на http://0.0.0.0:5000")
        http_server = WSGIServer(("0.0.0.0", 5000), app)
        http_server.serve_forever()
