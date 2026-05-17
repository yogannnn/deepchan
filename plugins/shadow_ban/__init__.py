from flask import current_app, g

from models import Ban


def init_app(app):
    def on_before_render(post, **kwargs):
        # Только если у поста есть identity_hash
        if not post.identity_hash:
            return

        # Проверяем активный теневой бан (identity_hash есть в таблице ban)
        banned = Ban.query.filter_by(
            identity_hash=post.identity_hash, active=True
        ).first()

        if not banned:
            return

        # Текущий зритель (может быть None)
        viewer_identity = getattr(g, "identity", {})
        viewer_id = viewer_identity.get("id") if viewer_identity else None

        # Если зритель — сам автор, он видит свои посты
        if viewer_id and viewer_id == post.identity_hash:
            return

        # Для всех остальных — скрываем содержимое
        post.comment = "[пост скрыт]"
        post.subject = None
        # Обнуляем файлы (только в памяти, не в БД)
        if hasattr(post, "files"):
            post.files = []

    app.on("posts.before_render", on_before_render)
