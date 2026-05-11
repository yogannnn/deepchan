import re
import time
from datetime import datetime, timezone

from flask import abort, current_app, request

from models import Ban, WordFilter

_last_post_time = {}


def check_rate_limit():
    ip = request.remote_addr
    now = time.time()
    if ip in _last_post_time:
        elapsed = now - _last_post_time[ip]
        limit = current_app.config["SETTINGS"].rate_limit_seconds
        if elapsed < limit:
            abort(
                429, description=f"Слишком часто. Подождите {limit - int(elapsed)} сек."
            )
    _last_post_time[ip] = now


def check_ban(ip):
    now = datetime.now(timezone.utc)
    ban = Ban.query.filter(
        Ban.ip_pattern == ip,
        Ban.active == True,
        (Ban.expires_at == None) | (Ban.expires_at > now),
    ).first()
    if ban:
        abort(403, description=f"Вы забанены. Причина: {ban.reason or 'не указана'}")


def apply_word_filters(text):
    filters = WordFilter.query.filter_by(active=True).all()
    for f in filters:
        if f.is_regex:
            if re.search(f.pattern, text, re.IGNORECASE):
                if f.action == "block":
                    abort(
                        400,
                        description=f"Сообщение содержит запрещённое выражение: {f.pattern}",
                    )
                elif f.action == "replace":
                    text = re.sub(f.pattern, f.replacement, text, flags=re.IGNORECASE)
        else:
            if f.pattern.lower() in text.lower():
                if f.action == "block":
                    abort(
                        400,
                        description=f"Сообщение содержит запрещённое слово: {f.pattern}",
                    )
                elif f.action == "replace":
                    text = text.replace(f.pattern, f.replacement)
    return text
