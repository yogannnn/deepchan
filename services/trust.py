"""
Сервис для подсчёта уровня доверия (trust score) на основе identity_hash.
Используется для identity-based капчи, теневого бана и репутации.
"""
from datetime import datetime, timezone

from sqlalchemy import func

from models import Ban, Post, Report, db


def get_trust_score(identity_hash):
    """Возвращает trust_score (0–100) для identity_hash. 100 = максимальное доверие."""
    if not identity_hash:
        return 50  # Нет identity — среднее доверие

    # Количество постов
    posts_count = Post.query.filter_by(identity_hash=identity_hash).count()

    # Количество жалоб на посты этого identity
    reports_count = (
        db.session.query(func.count(Report.id))
        .join(Post, Report.post_id == Post.id)
        .filter(Post.identity_hash == identity_hash)
        .scalar()
    ) or 0

    # Количество банов
    bans_count = Ban.query.filter_by(identity_hash=identity_hash, active=True).count()

    # Дата первого поста (возраст identity)
    first_post = (
        Post.query.filter_by(identity_hash=identity_hash)
        .order_by(Post.created_at.asc())
        .first()
    )
    age_days = 0
    if first_post:
        age_days = (
            datetime.now(timezone.utc)
            - first_post.created_at.replace(tzinfo=timezone.utc)
        ).days

    # Вычисляем trust_score (простая формула)
    score = 50  # базовый
    score += min(posts_count, 20) * 1  # до +20 за посты
    score -= reports_count * 5  # -5 за каждую жалобу
    score -= bans_count * 20  # -20 за каждый бан
    score += min(age_days, 30) * 0.5  # до +15 за "возраст"

    return max(0, min(100, int(score)))
