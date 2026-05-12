from flask import current_app
from sqlalchemy import inspect

from models import Setting, db


class Settings:
    DEFAULTS = {
        "SITE_TITLE": "DeepChan",
        "THREADS_PER_PAGE": 50,
        "POSTS_PER_PAGE": 50,
        "MAX_FILES": 4,
        "ALLOWED_EXTENSIONS": "jpg,jpeg,png,gif,webp,mp4,webm,mov,mp3,ogg,flac,wav,m4a",
        "MAX_CONTENT_LENGTH": 10485760,
        "MAX_IMAGE_DIMENSION": 5000,
        "MAX_VIDEO_DURATION": 180,
        "MAX_VIDEO_SIZE": 52428800,
        "MAX_AUDIO_DURATION": 600,
        "MAX_AUDIO_SIZE": 31457280,
        "WEBP_CONVERT_ENABLED": True,
        "STEALTH_TRIM": True,
        "RADIO_ENABLED": True,
        "RADIO_BITRATE": "128k",
        "RADIO_FOLDER": "/opt/deepchan/static/radio",
        "CAPTCHA_ENABLED": True,
        "AUTO_REFRESH_ENABLED": True,
        "AUTO_REFRESH_INTERVAL": 30,
        "RATE_LIMIT_SECONDS": 30,
        "STATS_SHOW_IPS": False,
        "BOARD_CLOSED": False,
        "REPORTS_ENABLED": True,
        "HEADER_HTML": "",
        "FOOTER_HTML": "",
        "ANNOUNCEMENT_HTML": "",
        "ADMIN_TRIP_SECRET": "",
        "DEPLOY_MODE": "production",
        "SITE_URL": "http://deepchan.i2p",
        "SITE_LANG": "ru",
    }
    BOOL_KEYS = {
        "WEBP_CONVERT_ENABLED",
        "STEALTH_TRIM",
        "RADIO_ENABLED",
        "CAPTCHA_ENABLED",
        "AUTO_REFRESH_ENABLED",
        "STATS_SHOW_IPS",
        "BOARD_CLOSED",
        "REPORTS_ENABLED",
    }
    INT_KEYS = {
        "THREADS_PER_PAGE",
        "POSTS_PER_PAGE",
        "MAX_FILES",
        "MAX_CONTENT_LENGTH",
        "MAX_IMAGE_DIMENSION",
        "MAX_VIDEO_DURATION",
        "MAX_VIDEO_SIZE",
        "MAX_AUDIO_DURATION",
        "MAX_AUDIO_SIZE",
        "AUTO_REFRESH_INTERVAL",
        "RATE_LIMIT_SECONDS",
    }

    def __init__(self, app=None):
        self.app = app
        self._cache = {}

    def load(self):
        self._cache = {}
        if not inspect(db.engine).has_table("setting"):
            return
        for key, default in self.DEFAULTS.items():
            row = Setting.query.filter_by(key=key).first()
            value = row.value if row else default
            self._cache[key] = self._convert(key, value)

        # Синхронизируем с app.config (для тестов и шаблонов)
        if self.app:
            self.app.config.update(self._cache)

    def _convert(self, key, value):
        if key in self.BOOL_KEYS:
            if isinstance(value, bool):
                return value
            return str(value).lower() in ("1", "true", "yes", "on")
        if key in self.INT_KEYS:
            try:
                return int(value)
            except Exception:
                return int(self.DEFAULTS[key])
        if key == "ALLOWED_EXTENSIONS":
            if isinstance(value, list):
                return value
            return [x.strip().lower() for x in str(value).split(",") if x.strip()]
        return str(value)

    def __getattr__(self, name):
        key = name.upper()
        # Сначала пытаемся взять из app.config (для тестов), затем из кеша, затем из DEFAULTS
        if self.app and key in self.app.config:
            return self._convert(key, self.app.config[key])
        if key in self._cache:
            return self._cache[key]
        if key in self.DEFAULTS:
            return self._convert(key, self.DEFAULTS[key])
        raise AttributeError(name)
