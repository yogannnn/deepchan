"""Сервис для работы с пользовательскими предпочтениями."""
from sqlalchemy import text

from models import db

# Разрешённые колонки в user_preferences – жёсткий whitelist
_ALLOWED_COLUMNS = {"language", "is_admin", "theme", "hidden_boards"}


def _check_key(key: str) -> None:
    if key not in _ALLOWED_COLUMNS:
        raise ValueError(f"Invalid preference key: {key}")


def get_preference(identity_hash: str, key: str) -> str | None:
    """Возвращает значение настройки или None."""
    _check_key(key)
    # Безопасная интерполяция: имя колонки проверено по whitelist
    query = f"SELECT {key} FROM user_preferences WHERE identity_hash = :hid"
    row = db.session.execute(text(query), {"hid": identity_hash}).fetchone()
    return row[0] if row else None


def set_preference(identity_hash: str, key: str, value: str) -> None:
    """Устанавливает настройку. Создаёт запись, если её нет."""
    _check_key(key)
    exists = db.session.execute(
        text("SELECT identity_hash FROM user_preferences WHERE identity_hash = :hid"),
        {"hid": identity_hash},
    ).fetchone()
    if not exists:
        insert_query = (
            f"INSERT INTO user_preferences (identity_hash, {key}) VALUES (:hid, :val)"
        )
        db.session.execute(
            text(insert_query),
            {"hid": identity_hash, "val": value},
        )
    else:
        update_query = f"UPDATE user_preferences SET {key} = :val, updated_at = CURRENT_TIMESTAMP WHERE identity_hash = :hid"
        db.session.execute(
            text(update_query),
            {"hid": identity_hash, "val": value},
        )
    db.session.commit()
