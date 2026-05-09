import os
from sqlalchemy import inspect, text
from flask import current_app
from models import Setting


def load_settings(app):
    with app.app_context():
        app.config["DEPLOY_MODE"] = os.environ.get("DEPLOY_MODE", "production")
        if not inspect(db.engine).has_table("setting"):
            return
        settings = Setting.query.all()
        for s in settings:
            if s.key == "DEPLOY_MODE":
                continue
            if s.key in (
                "CAPTCHA_ENABLED",
                "STATS_SHOW_IPS",
                "BOARD_CLOSED",
                "AUTO_REFRESH_ENABLED",
                "REPORTS_ENABLED",
            ):
                app.config[s.key] = s.value == "True"
            elif s.key in (
                "AUTO_REFRESH_INTERVAL",
                "RATE_LIMIT_SECONDS",
                "THREADS_PER_PAGE",
                "POSTS_PER_PAGE",
                "MAX_FILES",
                "MAX_CONTENT_LENGTH",
                "MAX_IMAGE_DIMENSION",
                "MAX_VIDEO_DURATION",
                "MAX_VIDEO_SIZE",
                "MAX_AUDIO_DURATION",
                "MAX_AUDIO_SIZE",
            ):
                app.config[s.key] = int(s.value) if s.value.isdigit() else 5000
            elif s.key in ("HEADER_HTML", "FOOTER_HTML", "SITE_TITLE"):
                app.config[s.key] = s.value
            elif s.key == "ALLOWED_EXTENSIONS":
                app.config["ALLOWED_EXTENSIONS"] = (
                    s.value.split(",") if s.value else ["jpg", "jpeg", "png", "gif"]
                )
            elif s.key == "WEBP_CONVERT_ENABLED":
                app.config["WEBP_CONVERT_ENABLED"] = s.value == "True"
            elif s.key == "STEALTH_TRIM":
                app.config["STEALTH_TRIM"] = s.value == "True"
            elif s.key == "RADIO_ENABLED":
                app.config["RADIO_ENABLED"] = s.value == "True"
            elif s.key == "RADIO_BITRATE":
                app.config["RADIO_BITRATE"] = s.value
            elif s.value == "True":
                app.config[s.key] = True
            elif s.value == "False":
                app.config[s.key] = False
            elif s.value.isdigit():
                app.config[s.key] = int(s.value)
            else:
                app.config[s.key] = s.value
