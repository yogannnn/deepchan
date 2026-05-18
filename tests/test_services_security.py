import time
from unittest.mock import patch

import pytest
from flask import g

from models import Ban, WordFilter, db
from services.security import apply_word_filters, check_ban, check_rate_limit


def test_check_rate_limit_first_request(app):
    """Первый запрос не должен блокироваться."""
    with app.app_context(), app.test_request_context():
        from services import security

        security._last_post_time.clear()
        check_rate_limit()


def test_check_rate_limit_too_fast(app):
    """Повторный запрос от того же identity за короткое время — 429."""
    with app.app_context(), app.test_request_context():
        from services import security

        security._last_post_time.clear()
        app.config["RATE_LIMIT_SECONDS"] = 30
        with patch("time.time", return_value=1000.0):
            check_rate_limit()
        with patch("time.time", return_value=1005.0):
            with pytest.raises(Exception) as exc:
                check_rate_limit()
            assert exc.value.code == 429


def test_check_rate_limit_with_identity(app):
    """Если в g.identity есть id, используется он, а не IP."""
    with app.app_context(), app.test_request_context():
        from services import security

        security._last_post_time.clear()
        app.config["RATE_LIMIT_SECONDS"] = 30
        with patch("time.time", return_value=2000.0):
            g.identity = {"id": "user123"}
            check_rate_limit()
        with patch("time.time", return_value=2010.0):
            g.identity = {"id": "user123"}
            with pytest.raises(Exception) as exc:
                check_rate_limit()
            assert exc.value.code == 429


def test_check_ban_no_ban(app):
    """Нет активного бана — вызов проходит."""
    with app.app_context(), app.test_request_context():
        g.identity = {"id": "not_banned"}
        check_ban()


def test_check_ban_banned_identity(app):
    """Активный бан на identity_hash вызывает 403 (ищем по ip_pattern)."""
    with app.app_context(), app.test_request_context():
        ban = Ban(ip_pattern="banned_user", reason="Test", active=True)
        db.session.add(ban)
        db.session.commit()

        g.identity = {"id": "banned_user"}
        with pytest.raises(Exception) as exc:
            check_ban()
        assert exc.value.code == 403


def test_check_ban_expired(app):
    """Бан с истекшим сроком не активен."""
    with app.app_context(), app.test_request_context():
        from datetime import datetime, timedelta, timezone

        ban = Ban(
            ip_pattern="expired_user",
            reason="Test",
            active=True,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db.session.add(ban)
        db.session.commit()

        g.identity = {"id": "expired_user"}
        check_ban()  # не должно вызывать ошибок


def test_apply_word_filters_replace(app):
    """Простое слово заменяется."""
    with app.app_context():
        wf = WordFilter(
            pattern="плохоеслово", replacement="***", action="replace", active=True
        )
        db.session.add(wf)
        db.session.commit()

        text = "Это плохоеслово в тексте"
        result = apply_word_filters(text)
        assert "плохоеслово" not in result
        assert "***" in result


def test_apply_word_filters_block(app):
    """Слово с action=block вызывает abort 400."""
    with app.app_context():
        wf = WordFilter(pattern="запрещено", action="block", active=True)
        db.session.add(wf)
        db.session.commit()

        with pytest.raises(Exception) as exc:
            apply_word_filters("здесь запрещено слово")
        assert exc.value.code == 400


def test_apply_word_filters_regex(app):
    """Регулярное выражение работает."""
    with app.app_context():
        wf = WordFilter(
            pattern=r"\bтест\d+\b",
            replacement="[HIDDEN]",
            is_regex=True,
            action="replace",
            active=True,
        )
        db.session.add(wf)
        db.session.commit()

        result = apply_word_filters("это тест123 и тест456")
        assert "тест123" not in result
        assert "[HIDDEN]" in result
