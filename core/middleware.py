import time
import random


class ParanoidMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        def custom_start_response(status, headers, exc_info=None):
            new_headers = [
                (k, v) for k, v in headers if k not in ("Server", "X-Powered-By")
            ]
            return start_response(status, new_headers, exc_info)

        time.sleep(random.uniform(0.005, 0.05))
        return self.app(environ, custom_start_response)
