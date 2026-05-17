from flask import g

from services.trust import get_trust_score

TRUST_THRESHOLD = 70  # Ниже этого score — капча обязательна


def init_app(app):
    @app.before_request
    def apply_identity_captcha():
        identity = getattr(g, "identity", None)
        if identity and identity.get("id"):
            score = get_trust_score(identity["id"])
            if score < TRUST_THRESHOLD:
                g.captcha_required = True
