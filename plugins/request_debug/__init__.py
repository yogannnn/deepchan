import logging
import pprint
from logging.handlers import RotatingFileHandler

from flask import request

LOG_FILE = "/opt/deepchan/logs/requests_debug.log"
LOG_FULL_ENVIRON = True  # Поставь False, если нужно меньше данных
LOG_REQUEST_DATA = True  # Поставь False для GET-запросов


def init_app(app):
    logger = logging.getLogger("request_debug")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=2)
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        logger.addHandler(handler)

    logger.info("=== request_debug plugin loaded ===")

    @app.before_request
    def debug_request():
        info = {
            "method": request.method,
            "url": request.url,
            "path": request.path,
            "remote_addr": request.remote_addr,
            "user_agent": request.headers.get("User-Agent"),
            "referrer": request.headers.get("Referer"),
            "headers": dict(request.headers),
            "cookies": dict(request.cookies),
            "args": dict(request.args),
            "form": dict(request.form) if request.form else None,
            "is_secure": request.is_secure,
            "host": request.host,
        }

        if LOG_FULL_ENVIRON:
            # Полное WSGI-окружение (может быть очень объёмным)
            info["environ"] = dict(request.environ)

        if LOG_REQUEST_DATA and request.method in ("POST", "PUT", "PATCH"):
            try:
                info["data"] = request.get_data(as_text=True)[
                    :2000
                ]  # первые 2000 символов
            except Exception:
                info["data"] = "<не удалось прочитать>"

        logger.info(f"\n{pprint.pformat(info)}")
