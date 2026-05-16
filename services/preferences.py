"""Сервис для работы с пользовательскими предпочтениями."""
from sqlalchemy import text

from models import db


def get_preference(identity_hash, key):
    """Возвращает значение настройки или None."""
    # Параметризованный запрос
    row = db.session.execute(
        text(f"SELECT {key} FROM user_preferences WHERE identity_hash = :hid"),
        {"hid": identity_hash},
    ).fetchone()
    return row[0] if row else None


def set_preference(identity_hash, key, value):
    """Устанавливает настройку. Создаёт запись, если её нет."""
    exists = db.session.execute(
        text("SELECT identity_hash FROM user_preferences WHERE identity_hash = :hid"),
        {"hid": identity_hash},
    ).fetchone()
    if not exists:
        db.session.execute(
            text(
                f"INSERT INTO user_preferences (identity_hash, {key}) VALUES (:hid, :val)"
            ),
            {"hid": identity_hash, "val": value},
        )
    else:
        db.session.execute(
            text(
                f"UPDATE user_preferences SET {key} = :val, updated_at = CURRENT_TIMESTAMP WHERE identity_hash = :hid"
            ),
            {"hid": identity_hash, "val": value},
        )
    db.session.commit()
