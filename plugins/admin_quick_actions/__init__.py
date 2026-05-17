import os
from functools import wraps

from flask import Blueprint, abort, current_app, g, redirect, request, url_for

from models import Ban, Board, Post, Thread, db
from services.preferences import get_preference, set_preference

admin_bp = Blueprint("admin_quick", __name__, url_prefix="/admin-quick")


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not getattr(g, "is_admin", False):
            abort(403)
        return f(*args, **kwargs)

    return decorated


def csrf_protect(action):
    def decorator(f):
        from flask import abort, request

        from services.csrf import verify_csrf_token

        @wraps(f)
        def decorated(*args, **kwargs):
            if request.method == "POST":
                token = request.form.get("csrf_token")
                timestamp = request.form.get("csrf_timestamp")
                if not token or not timestamp:
                    abort(403, description="CSRF token missing")
                if not verify_csrf_token(
                    "admin_quick",
                    action,
                    token,
                    timestamp,
                    current_app.config["SECRET_KEY"],
                ):
                    abort(403, description="CSRF token invalid")
            return f(*args, **kwargs)

        return decorated

    return decorator


@admin_bp.route("/delete-board/<int:board_id>", methods=["POST"])
@admin_required
@csrf_protect("delete_board")
def delete_board(board_id):
    board = Board.query.get_or_404(board_id)
    db.session.delete(board)
    db.session.commit()
    return redirect(url_for("main.index"))


@admin_bp.route("/delete-thread/<int:thread_id>", methods=["POST"])
@admin_required
@csrf_protect("delete_thread")
def delete_thread(thread_id):
    thread = Thread.query.get_or_404(thread_id)
    db.session.delete(thread)
    db.session.commit()
    return redirect(request.referrer or url_for("main.index"))


@admin_bp.route("/delete-post/<int:post_id>", methods=["POST"])
@admin_required
@csrf_protect("delete_post")
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    return redirect(request.referrer or url_for("main.index"))


@admin_bp.route("/shadow-ban/<identity_hash>", methods=["POST"])
@admin_required
@csrf_protect("shadow_ban")
def shadow_ban(identity_hash):
    existing = Ban.query.filter_by(identity_hash=identity_hash, active=True).first()
    if not existing:
        ban = Ban(
            identity_hash=identity_hash,
            ip_pattern="0.0.0.0",
            reason="Теневой бан",
            active=True,
        )
        db.session.add(ban)
        db.session.commit()
    return redirect(request.referrer or url_for("main.index"))


@admin_bp.route("/toggle-lock/<int:thread_id>", methods=["POST"])
@admin_required
@csrf_protect("toggle_lock")
def toggle_lock(thread_id):
    thread = Thread.query.get_or_404(thread_id)
    thread.is_locked = not thread.is_locked
    db.session.commit()
    return redirect(request.referrer or url_for("main.index"))


@admin_bp.route("/mark-admin", methods=["POST"])
@csrf_protect("mark_admin")
def mark_admin():
    """Сохраняет текущий identity как админский."""
    identity = getattr(g, "identity", {})
    if not identity or not identity.get("id"):
        flash("Не удалось определить identity. Вы используете I2P?", "error")
        return redirect(request.referrer or url_for("main.index"))
    set_preference(identity["id"], "is_admin", "true")
    flash("Быстрые кнопки активированы для вашего identity.", "success")
    return redirect(request.referrer or url_for("main.index"))


@admin_bp.route("/unmark-admin", methods=["POST"])
@csrf_protect("unmark_admin")
def unmark_admin():
    """Убирает админскую метку с текущего identity."""
    identity = getattr(g, "identity", {})
    if identity and identity.get("id"):
        set_preference(identity["id"], "is_admin", "false")
        flash("Быстрые кнопки отключены для вашего identity.", "success")
    return redirect(request.referrer or url_for("main.index"))


def init_app(app):
    app.register_blueprint(admin_bp)

    @app.before_request
    def check_admin():
        identity = getattr(g, "identity", {})
        if identity and identity.get("id"):
            try:
                if get_preference(identity["id"], "is_admin") == "true":
                    g.is_admin = True
            except Exception:
                pass

    # Кнопка "админ на месте" в меню админки
    def menu_item(**kwargs):
        identity = getattr(g, "identity", {})
        if identity and identity.get("id"):
            try:
                is_admin_marked = get_preference(identity["id"], "is_admin") == "true"
            except Exception:
                return ""

            # Генерируем CSRF-токен
            from services.csrf import generate_csrf_token

            token, ts = generate_csrf_token(
                "admin_quick", "mark_admin", current_app.config["SECRET_KEY"]
            )

            if is_admin_marked:
                return (
                    '<form method="post" action="/admin-quick/unmark-admin" style="display:inline;">'
                    f'<input type="hidden" name="csrf_token" value="{token}">'
                    f'<input type="hidden" name="csrf_timestamp" value="{ts}">'
                    '<button type="submit" class="btn-link" style="color:#ffaa00;">Отключить быстрые кнопки</button>'
                    "</form> |"
                )
            else:
                return (
                    '<form method="post" action="/admin-quick/mark-admin" style="display:inline;">'
                    f'<input type="hidden" name="csrf_token" value="{token}">'
                    f'<input type="hidden" name="csrf_timestamp" value="{ts}">'
                    '<button type="submit" class="btn-link" style="color:#66ff66;">Активировать быстрые кнопки</button>'
                    "</form> |"
                )
        return ""

    app.on("admin.menu_rendering", menu_item)

    # Кнопки рядом с тредами (на странице доски) – будут выводиться через шаблон, но здесь пример
    # Оставим существующие хуки, но они требуют доработки шаблонов. Пока отключим, чтобы не ломать.
    # Вместо этого можно просто показать админскую панель в подвале.
    def footer_widget(**kwargs):
        if not getattr(g, "is_admin", False):
            return ""
        return '<p style="text-align:center; color:#66ff66;">[Режим администратора]</p>'

    app.on("ui.footer_rendering", footer_widget)
