import io
import json
import os
import zipfile
from functools import wraps

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from models import Setting, db

admin_plugins_bp = Blueprint("admin_plugins", __name__, url_prefix="/admin")


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

        from services.csrf import verify_csrf_token

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


@admin_plugins_bp.route("/plugins")
@admin_required
def admin_plugins():
    """Страница управления плагинами."""
    plugins_dir = os.path.join(current_app.root_path, "plugins")
    plugins = []
    if os.path.isdir(plugins_dir):
        for name in os.listdir(plugins_dir):
            plugin_path = os.path.join(plugins_dir, name)
            manifest_path = os.path.join(plugin_path, "plugin.json")
            if not os.path.isfile(manifest_path):
                continue
            try:
                with open(manifest_path) as f:
                    manifest = json.load(f)
            except:
                manifest = {}
            enabled_key = f"plugin_{name}_enabled"
            try:
                s = Setting.query.filter_by(key=enabled_key).first()
                enabled = s.value.lower() == "true" if s else True
            except Exception:
                enabled = True
            loaded = (
                name in current_app.plugin_registry
                if hasattr(current_app, "plugin_registry")
                else False
            )
            plugins.append(
                {
                    "name": name,
                    "display_name": manifest.get("name", name),
                    "version": manifest.get("version", "?"),
                    "enabled": enabled,
                    "loaded": loaded,
                }
            )
    plugins.sort(key=lambda p: p.get("priority", 100))
    return render_template("admin/plugins.html", plugins=plugins)


@admin_plugins_bp.route("/plugins/toggle/<name>", methods=["POST"])
@admin_required
@csrf_protect("toggle_plugin")
def admin_toggle_plugin(name):
    """Включение/выключение плагина."""
    enabled_key = f"plugin_{name}_enabled"
    s = Setting.query.filter_by(key=enabled_key).first()
    if not s:
        s = Setting(key=enabled_key, value="true")
    current = s.value.lower() == "true"
    s.value = "false" if current else "true"
    db.session.add(s)
    db.session.commit()
    flash(
        f"Плагин {name} {'отключён' if current else 'включён'}. Требуется перезапуск приложения.",
        "success",
    )
    return redirect(url_for("admin_plugins.admin_plugins"))


@admin_plugins_bp.route("/plugins/upload", methods=["POST"])
@admin_required
@csrf_protect("upload_plugin")
def admin_upload_plugin():
    """Загрузка zip-архива с плагином."""
    f = request.files.get("plugin_zip")
    if not f or not f.filename.endswith(".zip"):
        flash("Требуется .zip архив", "error")
        return redirect(url_for("admin_plugins.admin_plugins"))
    try:
        with zipfile.ZipFile(io.BytesIO(f.read())) as zf:
            for member in zf.namelist():
                if member.startswith("/") or ".." in member:
                    flash("Некорректные пути в архиве", "error")
                    return redirect(url_for("admin_plugins.admin_plugins"))
            plugin_json = None
            for name in zf.namelist():
                if name.endswith("/plugin.json") or name == "plugin.json":
                    plugin_json = name
                    break
            if not plugin_json:
                flash("plugin.json не найден в архиве", "error")
                return redirect(url_for("admin_plugins.admin_plugins"))
            plugin_dir = (
                os.path.dirname(plugin_json)
                or os.path.splitext(os.path.basename(plugin_json))[0]
            )
            plugin_dir = os.path.normpath(plugin_dir).strip()
            if (
                not plugin_dir
                or plugin_dir in (".", "..")
                or os.path.isabs(plugin_dir)
                or plugin_dir.startswith("..")
            ):
                flash("Некорректная директория плагина", "error")
                return redirect(url_for("admin_plugins.admin_plugins"))

            plugins_root = os.path.abspath(
                os.path.join(current_app.root_path, "plugins")
            )
            target_dir = os.path.abspath(
                os.path.normpath(os.path.join(plugins_root, plugin_dir))
            )
            if os.path.commonpath([plugins_root, target_dir]) != plugins_root:
                flash("Некорректная директория плагина", "error")
                return redirect(url_for("admin_plugins.admin_plugins"))

            for member in zf.namelist():
                member_target = os.path.abspath(
                    os.path.normpath(os.path.join(target_dir, member))
                )
                if os.path.commonpath([target_dir, member_target]) != target_dir:
                    flash("Некорректные пути в архиве", "error")
                    return redirect(url_for("admin_plugins.admin_plugins"))

            os.makedirs(target_dir, exist_ok=True)
            zf.extractall(target_dir)
        enabled_key = f"plugin_{plugin_dir}_enabled"
        if not Setting.query.get(enabled_key):
            db.session.add(Setting(key=enabled_key, value="false"))
            db.session.commit()
        flash(
            f"Плагин {plugin_dir} загружен. Включите его и перезапустите приложение.",
            "success",
        )
    except Exception as e:
        flash(f"Ошибка загрузки плагина: {e}", "error")
    return redirect(url_for("admin_plugins.admin_plugins"))
