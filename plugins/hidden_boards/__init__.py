import os
from functools import wraps

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template_string,
    request,
    url_for,
)

from models import Board, Setting, db
from services.boards import get_boards

HIDDEN_BOARDS_KEY = "plugin_hidden_boards"

admin_bp = Blueprint("hidden_boards", __name__, url_prefix="/admin")


def admin_required(f):
    from flask import Response, request

    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.password != current_app.config["ADMIN_PASSWORD"]:
            return Response(
                "Введите логин и пароль.",
                401,
                {"WWW-Authenticate": 'Basic realm="Admin Area"'},
            )
        return f(*args, **kwargs)

    return decorated


def csrf_protect(action):
    def decorator(f):
        from flask import abort, request

        from utils import verify_csrf_token

        @wraps(f)
        def decorated(*args, **kwargs):
            if request.method == "POST":
                user_id = (
                    request.authorization.username
                    if request.authorization
                    else "anonymous"
                )
                token = request.form.get("csrf_token")
                timestamp = request.form.get("csrf_timestamp")
                if not token or not timestamp:
                    abort(403, description="CSRF token missing")
                if not verify_csrf_token(
                    user_id, action, token, timestamp, current_app.config["SECRET_KEY"]
                ):
                    abort(403, description="CSRF token invalid")
            return f(*args, **kwargs)

        return decorated

    return decorator


TEMPLATE = """
{% extends "admin/base.html" %}
{% block admin_content %}
<h2>Скрытие досок</h2>
<form method="post">
    {% set csrf = csrf_token("hidden_boards") %}
    <input type="hidden" name="csrf_token" value="{{ csrf.token }}">
    <input type="hidden" name="csrf_timestamp" value="{{ csrf.timestamp }}">
    <table class="admin-table">
        <thead><tr><th>Доска</th><th>Скрыта</th></tr></thead>
        <tbody>
        {% for b in boards %}
        <tr>
            <td>/{{ b.short_name }}/ - {{ b.name }}</td>
            <td><input type="checkbox" name="hidden" value="{{ b.short_name }}" {% if b.short_name in hidden %}checked{% endif %}></td>
        </tr>
        {% endfor %}
        </tbody>
    </table>
    <button type="submit" class="btn">Сохранить</button>
</form>
{% endblock %}
"""


@admin_bp.route("/hidden_boards", methods=["GET", "POST"])
@admin_required
@csrf_protect("hidden_boards")
def manage():
    if request.method == "POST":
        selected = request.form.getlist("hidden")
        value = ",".join(selected)
        s = Setting.query.filter_by(key=HIDDEN_BOARDS_KEY).first()
        if not s:
            s = Setting(key=HIDDEN_BOARDS_KEY)
        s.value = value
        db.session.add(s)
        db.session.commit()
        current_app.config["SETTINGS"]._cache[HIDDEN_BOARDS_KEY] = value
        flash("Список скрытых досок обновлён.", "success")
        return redirect(url_for("hidden_boards.manage"))

    s = Setting.query.filter_by(key=HIDDEN_BOARDS_KEY).first()
    hidden = s.value.split(",") if s and s.value else []
    boards = Board.query.order_by(Board.position).all()
    return render_template_string(TEMPLATE, boards=boards, hidden=hidden)


def init_app(app):
    # Удаляем возможный старый Blueprint (конфликт имён после пересоздания)
    if "hidden_boards" in app.blueprints:
        del app.blueprints["hidden_boards"]
    app.register_blueprint(admin_bp)

    def filter_boards(boards, **kwargs):
        s = Setting.query.filter_by(key=HIDDEN_BOARDS_KEY).first()
        hidden = s.value.split(",") if s and s.value else []
        if hidden:
            boards[:] = [b for b in boards if b.short_name not in hidden]

    app.on("boards.filter_list", filter_boards)

    def menu_item(**kwargs):
        return '<a href="/admin/hidden_boards">👁️ Скрытие досок</a> |'

    app.on("admin.menu_rendering", menu_item)
