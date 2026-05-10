from flask import current_app
from models import Setting
from sqlalchemy import inspect


class Settings:
    _instance = None

    def __init__(self, app=None):
        self.app = app
        self._cache = {}
        if app:
            self.load()

    def load(self):
        from models import db

        with self.app.app_context():
            if not inspect(db.engine).has_table("setting"):
                return
            for s in Setting.query.all():
                self._cache[s.key] = s.value
                # Заполняем app.config для совместимости с шаблонами
                self.app.config[s.key] = s.value

    # Типизированные свойства
    @property
    def site_title(self):
        return self._cache.get("SITE_TITLE", "Имиджборда")

    @property
    def threads_per_page(self):
        return int(self._cache.get("THREADS_PER_PAGE", 30))

    @property
    def posts_per_page(self):
        return int(self._cache.get("POSTS_PER_PAGE", 50))

    @property
    def max_files(self):
        return int(self._cache.get("MAX_FILES", 4))

    @property
    def allowed_extensions(self):
        val = self._cache.get("ALLOWED_EXTENSIONS", "jpg,jpeg,png,gif")
        return (
            [x.strip().lower() for x in val.split(",")]
            if val
            else ["jpg", "jpeg", "png", "gif"]
        )

    @property
    def max_content_length(self):
        return int(self._cache.get("MAX_CONTENT_LENGTH", 10 * 1024 * 1024))

    @property
    def max_image_dimension(self):
        return int(self._cache.get("MAX_IMAGE_DIMENSION", 5000))

    @property
    def max_video_duration(self):
        return int(self._cache.get("MAX_VIDEO_DURATION", 180))

    @property
    def max_video_size(self):
        return int(self._cache.get("MAX_VIDEO_SIZE", 50 * 1024 * 1024))

    @property
    def max_audio_duration(self):
        return int(self._cache.get("MAX_AUDIO_DURATION", 600))

    @property
    def max_audio_size(self):
        return int(self._cache.get("MAX_AUDIO_SIZE", 30 * 1024 * 1024))

    @property
    def webp_convert_enabled(self):
        return self._cache.get("WEBP_CONVERT_ENABLED", "True") == "True"

    @property
    def stealth_trim(self):
        return self._cache.get("STEALTH_TRIM", "True") == "True"

    @property
    def radio_enabled(self):
        return self._cache.get("RADIO_ENABLED", "True") == "True"

    @property
    def radio_bitrate(self):
        return self._cache.get("RADIO_BITRATE", "128k")

    @property
    def captcha_enabled(self):
        return self._cache.get("CAPTCHA_ENABLED", "False") == "True"

    @property
    def auto_refresh_enabled(self):
        return self._cache.get("AUTO_REFRESH_ENABLED", "True") == "True"

    @property
    def auto_refresh_interval(self):
        return int(self._cache.get("AUTO_REFRESH_INTERVAL", 30))

    @property
    def rate_limit_seconds(self):
        return int(self._cache.get("RATE_LIMIT_SECONDS", 30))

    @property
    def stats_show_ips(self):
        return self._cache.get("STATS_SHOW_IPS", "False") == "True"

    @property
    def board_closed(self):
        return self._cache.get("BOARD_CLOSED", "False") == "True"

    @property
    def reports_enabled(self):
        return self._cache.get("REPORTS_ENABLED", "True") == "True"

    @property
    def header_html(self):
        return self._cache.get("HEADER_HTML", "")

    @property
    def footer_html(self):
        return self._cache.get("FOOTER_HTML", "")

    @property
    def announcement_html(self):
        return self._cache.get("ANNOUNCEMENT_HTML", "")

    @property
    def admin_trip_secret(self):
        return self._cache.get("ADMIN_TRIP_SECRET", "")

    @property
    def deploy_mode(self):
        return self._cache.get("DEPLOY_MODE", "production")

    @property
    def site_url(self):
        return self._cache.get("SITE_URL", "http://127.0.0.1:5000")
