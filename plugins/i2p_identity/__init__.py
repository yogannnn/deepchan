import hashlib

from flask import current_app, g, request


def init_app(app):
    @app.before_request
    def build_identity():
        raw = request.headers.get("X-I2P-DestB32") or request.headers.get(
            "X-I2P-DestHash"
        )
        if raw:
            secret = current_app.config.get("SECRET_KEY", "default-secret")
            anon_id = hashlib.sha256(f"{raw}{secret}".encode()).hexdigest()[:16]
            transport = "i2p"
        else:
            anon_id = None
            transport = "unknown"
        g.identity = {"id": anon_id, "transport": transport}
