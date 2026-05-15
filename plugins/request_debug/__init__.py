import logging
import pprint
from logging.handlers import RotatingFileHandler

from flask import request

LOG_FILE = "/opt/deepchan/logs/requests_debug.log"


def init_app(app):
    # Создаём отдельный логгер для этого плагина
    logger = logging.getLogger("request_debug")
    logger.setLevel(logging.INFO)

    # Чтобы не дублировались записи при перезагрузке плагина
    if not logger.handlers:
        handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=2)
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        logger.addHandler(handler)

    def debug_request(**kwargs):
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
        logger.info(f"\n{pprint.pformat(info)}")

    app.on("http.before_request", debug_request)
