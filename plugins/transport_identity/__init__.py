import hashlib

from flask import current_app, g, request


def init_app(app):
    @app.before_request
    def build_identity():
        raw_i2p = request.headers.get("X-I2P-DestB32") or request.headers.get(
            "X-I2P-DestHash"
        )
        host = request.headers.get("Host", "").lower()

        secret = current_app.config.get("SECRET_KEY", "default-secret")

        # 1. I2P
        if raw_i2p:
            anon_id = hashlib.sha256(f"{raw_i2p}{secret}".encode()).hexdigest()[:16]
            g.identity = {"id": anon_id, "transport": "i2p"}
        # 2. Tor: определяем по onion-хосту и формируем хеш из UA + Accept-Language
        elif host.endswith(".onion") or (".onion:" in host):
            ua = request.headers.get("User-Agent", "unknown")
            al = request.headers.get("Accept-Language", "unknown")
            raw = f"{ua}{al}"
            anon_id = hashlib.sha256(f"{raw}{secret}".encode()).hexdigest()[:16]
            g.identity = {"id": anon_id, "transport": "tor"}
        # 3. Клирнет
        else:
            anon_id = hashlib.sha256(
                f"{request.remote_addr}{secret}".encode()
            ).hexdigest()[:16]
            g.identity = {"id": anon_id, "transport": "clearnet"}

        # Для Tor всегда минимальный trust_score
        if g.identity.get("transport") == "tor":
            g.trust_score_override = 0

    # Компактный виджет в подвале (только транспорт и ID)
    def footer_widget(**kwargs):
        ident = g.get("identity")
        if not ident:
            return ""

        transport = ident.get("transport", "unknown")
        short_id = ident.get("id", "?")[:12] if ident.get("id") else "?"

        # Если передан ?debug_headers=1, добавляем подробности
        if request.args.get("debug_headers") == "1":
            ip = request.remote_addr or "нет"
            host = request.headers.get("Host", "?")
            i2p = request.headers.get("X-I2P-DestB32", "нет")
            ua = request.headers.get("User-Agent", "?")[:40]
            details = f"<br>IP: {ip} | Host: {host}<br>I2P: {i2p} | UA: {ua}"
        else:
            details = ""

        return (
            f'<p style="color:#7ab37a; text-align:center; font-size:0.75rem;">'
            f"Transport: {transport} | ID: {short_id}{details}</p>"
        )

    app.on("ui.footer_rendering", footer_widget)
