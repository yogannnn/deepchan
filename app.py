from flask import Flask, render_template, request, session, make_response, redirect, url_for
from flask_compress import Compress
from config import Config
from models import db, Setting, RadioTrack, Post, Board, Thread, PostFTS
from utils import generate_csrf_token, verify_csrf_token, process_comment
from sqlalchemy import inspect, text
import os
import logging
from logging.handlers import RotatingFileHandler
import time
import random
import subprocess
from datetime import datetime, timezone

app = Flask(__name__)
Compress(app)
app.config.from_object(Config)
db.init_app(app)
app.secret_key = app.config['SECRET_KEY']

app.jinja_env.filters['process_comment'] = process_comment

if not app.debug:
    handler = RotatingFileHandler('logs/board.log', maxBytes=10000, backupCount=3)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'thumbs'), exist_ok=True)

def load_settings():
    with app.app_context():
        app.config['DEPLOY_MODE'] = os.environ.get('DEPLOY_MODE', 'production')
        if not inspect(db.engine).has_table('setting'):
            return
        settings = Setting.query.all()
        for s in settings:
            if s.key == 'DEPLOY_MODE':
                continue
            if s.key in ('CAPTCHA_ENABLED', 'STATS_SHOW_IPS', 'BOARD_CLOSED', 'AUTO_REFRESH_ENABLED'):
                app.config[s.key] = s.value == 'True'
            elif s.key in ('AUTO_REFRESH_INTERVAL', 'RATE_LIMIT_SECONDS', 'THREADS_PER_PAGE', 'POSTS_PER_PAGE', 'MAX_FILES', 'MAX_CONTENT_LENGTH', 'MAX_IMAGE_DIMENSION', 'MAX_VIDEO_DURATION', 'MAX_VIDEO_SIZE', 'MAX_AUDIO_DURATION', 'MAX_AUDIO_SIZE'):
                app.config[s.key] = int(s.value) if s.value.isdigit() else 5000
            elif s.key in ('HEADER_HTML', 'FOOTER_HTML', 'SITE_TITLE'):
                app.config[s.key] = s.value
            elif s.key == 'ALLOWED_EXTENSIONS':
                app.config['ALLOWED_EXTENSIONS'] = [x.strip().lower() for x in s.value.split(',')] if s.value else ['jpg', 'jpeg', 'png', 'gif']
            elif s.key == 'WEBP_CONVERT_ENABLED':
                app.config['WEBP_CONVERT_ENABLED'] = s.value == 'True'
            elif s.key == 'STEALTH_TRIM':
                app.config['STEALTH_TRIM'] = s.value == 'True'
            elif s.key == 'RADIO_ENABLED':
                app.config['RADIO_ENABLED'] = s.value == 'True'
            elif s.key == 'RADIO_BITRATE':
                app.config['RADIO_BITRATE'] = s.value
            elif s.value == 'True':
                app.config[s.key] = True
            elif s.value == 'False':
                app.config[s.key] = False
            elif s.value.isdigit():
                app.config[s.key] = int(s.value)
            else:
                app.config[s.key] = s.value

from blueprints.main import main_bp
from blueprints.board import board_bp
from blueprints.admin import admin_bp
from blueprints.radio import radio_bp

app.register_blueprint(main_bp)
app.register_blueprint(board_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(radio_bp)

@app.context_processor
def inject_csrf_token():
    def make_csrf_token(action):
        user_id = request.authorization.username if request.authorization else 'anonymous'
        token, timestamp = generate_csrf_token(user_id, action, app.config['SECRET_KEY'])
        return {'token': token, 'timestamp': timestamp}
    return dict(csrf_token=make_csrf_token)

@app.before_request
def check_board_closed():
    if app.config.get('BOARD_CLOSED', False):
        if request.path.startswith('/admin') or request.path.startswith('/static'):
            return
        if request.endpoint != 'board_closed':
            return render_template('board_closed.html'), 503

@app.route('/closed')
def board_closed():
    return render_template('board_closed.html')

class ParanoidMiddleware:
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        def custom_start_response(status, headers, exc_info=None):
            new_headers = [(k, v) for k, v in headers if k not in ('Server', 'X-Powered-By')]
            return start_response(status, new_headers, exc_info)
        time.sleep(random.uniform(0.005, 0.05))
        return self.app(environ, custom_start_response)

app.wsgi_app = ParanoidMiddleware(app.wsgi_app)

@app.after_request
def add_cache_headers(response):
    if request.path.startswith('/static'):
        response.cache_control.no_cache = False
        response.cache_control.no_store = False
        if request.path.endswith('.css') or '/fonts/' in request.path:
            response.cache_control.max_age = 604800
            response.cache_control.public = True
        elif request.path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
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

from flask_wtf.csrf import generate_csrf
app.jinja_env.globals['csrf_token'] = generate_csrf

# Кастомные страницы ошибок
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not inspect(db.engine).has_table('setting'):
            Setting.__table__.create(db.engine)
        if not inspect(db.engine).has_table('radio_track'):
            RadioTrack.__table__.create(db.engine)
        load_settings()
        with db.engine.connect() as conn:
            res = conn.execute(text("PRAGMA table_info(post)"))
            cols = [row[1] for row in res]
            if 'search_text' not in cols:
                conn.execute(text("ALTER TABLE post ADD COLUMN search_text TEXT"))
                conn.commit()
        for post in Post.query.all():
            if not post.search_text:
                post.search_text = (post.comment + ' ' + (post.subject or '')).lower()
        db.session.commit()
        with db.engine.connect() as conn:
            for table, col, col_type in [('post_file', 'md5_hash', 'VARCHAR(32)'),
                                         ('post_file', 'file_size', 'INTEGER DEFAULT 0'),
                                         ('post', 'ip_address', 'VARCHAR(45)'),
                                         ('post_file', 'file_type', 'VARCHAR(20) DEFAULT "image"'),
                                         ('post_file', 'duration', 'FLOAT')]:
                res = conn.execute(text(f"PRAGMA table_info({table.split()[0]})"))
                cols = [row[1] for row in res]
                if col not in cols:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
            conn.commit()
        insp = inspect(db.engine)
        if not insp.has_table('post_fts'):
            PostFTS.__table__.create(db.engine)
        if not Board.query.filter_by(short_name='b').first():
            b = Board(short_name='b', name='Бред', description='Общий раздел')
            db.session.add(b)
            db.session.commit()
    deploy_mode = app.config.get('DEPLOY_MODE', 'production')
    if deploy_mode == 'development':
        print("🚀 Запуск через Flask development server на http://0.0.0.0:5000")
        app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
    else:
        from gevent.pywsgi import WSGIServer
        print("🚀 Запуск через Gevent (стриминг) на http://0.0.0.0:5000")
        http_server = WSGIServer(('0.0.0.0', 5000), app)
        http_server.serve_forever()
@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html', description=e.description), 403

@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html', description=e.description), 404

@app.errorhandler(429)
def too_many_requests(e):
    return render_template('errors/429.html', description=e.description), 429

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html', description=e.description), 500
