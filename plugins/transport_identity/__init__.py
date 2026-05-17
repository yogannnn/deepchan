import hashlib
import secrets

from flask import current_app, g, make_response, request


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
            return

        # 2. Tor: определяем по onion-хосту
        if host.endswith(".onion") or (".onion:" in host):
            # Сначала пробуем взять ID из куки
            cookie_id = request.cookies.get("deepchan_tor_id")
            if cookie_id:
                g.identity = {"id": cookie_id, "transport": "tor"}
                g.tor_use_cookie = True  # флаг, что кука уже есть
            else:
                # Куки нет – генерируем новый токен и запомним, что нужно поставить куку
                new_id = secrets.token_hex(16)
                g.identity = {"id": new_id, "transport": "tor"}
                g.tor_set_cookie = new_id  # флаг для after_request
            # Fallback: если куки отключены, cookie_id будет None, и мы бы пошли в else,
            # но там всё равно генерируется новый токен, который будет жить до конца запроса.
            # Дополнительный fallback на заголовки не нужен, потому что новый токен и так стабилен в рамках сессии.
            g.trust_score_override = 0
            return

        # 3. Клирнет
        anon_id = hashlib.sha256(f"{request.remote_addr}{secret}".encode()).hexdigest()[
            :16
        ]
        g.identity = {"id": anon_id, "transport": "clearnet"}

    @app.after_request
    def set_tor_cookie(response):
        new_id = getattr(g, "tor_set_cookie", None)
        if new_id:
            response.set_cookie(
                "deepchan_tor_id",
                value=new_id,
                path="/",
                httponly=True,
                samesite="Lax",
                secure=False,  # для I2P/Tor обычно HTTP, поэтому False
            )
        return response

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
