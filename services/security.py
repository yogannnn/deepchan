import re
import time
from datetime import datetime, timezone

from flask import abort, current_app, g, request

from core.exceptions import BannedError, RateLimitError, ValidationError
from core.i18n import t
from models import Ban, WordFilter

_last_post_time = {}


def check_rate_limit():
    # Используем identity_hash из g.identity, если есть, иначе IP
    from flask import g

    identity = getattr(g, "identity", None)
    ip = identity.get("id") if identity and identity.get("id") else request.remote_addr
    now = time.time()
    if ip in _last_post_time:
        elapsed = now - _last_post_time[ip]
        limit = current_app.config["SETTINGS"].rate_limit_seconds
        if elapsed < limit:
            raise RateLimitError(t("rate_limit", seconds=limit - int(elapsed)))
    _last_post_time[ip] = now


def check_ban(ip=None):
    from flask import g

    if ip is None:
        identity = getattr(g, "identity", None)
        ip = (
            identity.get("id")
            if identity and identity.get("id")
            else request.remote_addr
        )
    now = datetime.now(timezone.utc)
    ban = Ban.query.filter(
        Ban.ip_pattern == ip,
        Ban.active == True,
        (Ban.expires_at == None) | (Ban.expires_at > now),
    ).first()
    if ban:
        raise BannedError(t("banned", reason=ban.reason or "не указана"))


def apply_word_filters(text):
    filters = WordFilter.query.filter_by(active=True).all()
    for f in filters:
        if f.is_regex:
            if re.search(f.pattern, text, re.IGNORECASE):
                if f.action == "block":
                    abort(
                        400,
                        description=t("wordfilter_block", pattern=f.pattern),
                    )
                elif f.action == "replace":
                    text = re.sub(f.pattern, f.replacement, text, flags=re.IGNORECASE)
        else:
            if f.pattern.lower() in text.lower():
                if f.action == "block":
                    abort(
                        400,
                        description=t("wordfilter_word", pattern=f.pattern),
                    )
                elif f.action == "replace":
                    text = text.replace(f.pattern, f.replacement)
    return text
