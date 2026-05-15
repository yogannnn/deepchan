import pprint

from flask import request


def init_app(app):
    def debug_request(**kwargs):
        # Собираем всю информацию о запросе
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
        app.logger.info(f"REQUEST DEBUG:\n{pprint.pformat(info)}")

    app.on("http.before_request", debug_request)
