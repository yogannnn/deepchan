import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'board.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'admin'
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    WTF_CSRF_ENABLED = False
#   CAPTCHA_ENABLED = False
    # Настройки flask-simple-captcha
    CAPTCHA_LENGTH = 4
    CAPTCHA_DIGITS = True
    CAPTCHA_EXCLUDE_VISUALLY_SIMILAR = True
    CAPTCHA_BACKGROUND_COLOR = '#0a0f0a'
    CAPTCHA_TEXT_COLOR = '#33cc33'
    CAPTCHA_FONT_SIZE = 32
    CAPTCHA_WIDTH = 200
    CAPTCHA_HEIGHT = 70
#   STATS_SHOW_IPS = False
