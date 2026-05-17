import hashlib
import secrets

from flask import current_app, g, request, url_for

from services.preferences import get_preference


def init_app(app):
    @app.before_request
    def build_identity():
        # 1. Определяем транспорт и получаем идентификатор
        raw = request.headers.get("X-I2P-DestB32") or request.headers.get(
            "X-I2P-DestHash"
        )
        if raw:
            # I2P
            secret = current_app.config.get("SECRET_KEY", "default-secret")
            anon_id = hashlib.sha256(f"{raw}{secret}".encode()).hexdigest()[:16]
            g.identity = {"id": anon_id, "transport": "i2p"}
        elif (
            request.remote_addr in ("127.0.0.1", "::1", "localhost", None)
            or not request.remote_addr
        ):
            # Tor или I2P без заголовков — считаем Tor
            session_id = request.args.get("sesid") or request.form.get("sesid")
            if not session_id:
                session_id = secrets.token_hex(16)
            g.identity = {"id": session_id, "transport": "tor"}
            g._sesid = session_id
        else:
            # Клирнет — хешируем IP
            secret = current_app.config.get("SECRET_KEY", "default-secret")
            anon_id = hashlib.sha256(
                f"{request.remote_addr}{secret}".encode()
            ).hexdigest()[:16]
            g.identity = {"id": anon_id, "transport": "clearnet"}

        # 2. Для Tor всегда минимальный trust_score
        if g.identity.get("transport") == "tor":
            g.trust_score_override = 0

    # Прокидываем sesid во все ссылки (только для Tor)
    @app.url_defaults
    def add_sesid(endpoint, values):
        if getattr(g, "_sesid", None) and endpoint != "static":
            values.setdefault("sesid", g._sesid)

    # Добавляем скрытое поле sesid во все формы (только для Tor)
    @app.context_processor
    def inject_sesid():
        sesid = getattr(g, "_sesid", None)
        if sesid:
            return {
                "sesid_field": f'<input type="hidden" name="sesid" value="{sesid}">'
            }
        return {}

    # Отладочный виджет в подвале — показывает транспорт, ID, IP и ключевые заголовки
    def footer_widget(**kwargs):
        ident = g.get("identity")
        if not ident:
            return ""
        transport = ident.get("transport", "unknown")
        short_id = ident.get("id", "?")[:12] if ident.get("id") else "?"
        ip = request.remote_addr or "нет"
        host = request.headers.get("Host", "?")
        i2p = request.headers.get("X-I2P-DestB32", "нет")
        ua = request.headers.get("User-Agent", "?")[:40]
        return (
            f'<p style="color:#7ab37a; text-align:center; font-size:0.75rem;">'
            f"Transport: {transport} | ID: {short_id}<br>"
            f"IP: {ip} | Host: {host}<br>"
            f"I2P: {i2p} | UA: {ua}</p>"
        )

    app.on("ui.footer_rendering", footer_widget)
