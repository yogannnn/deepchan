from functools import wraps

from flask import Blueprint, Response, current_app, render_template, request

debug_bp = Blueprint("debug", __name__, url_prefix="/admin/debug")


def admin_required(f):
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


@debug_bp.route("/plugins")
@admin_required
def debug_plugins():
    """Показывает загруженные плагины, их хуки и приоритеты."""
    plugins_info = []
    for name, data in current_app.plugin_registry.items():
        manifest = data.get("manifest", {})
        hooks = []
        for event, callbacks in current_app.events.items():
            for cb in callbacks:
                if hasattr(cb, "__qualname__"):
                    module_name = data["module"].__name__
                    if module_name in cb.__qualname__:
                        hooks.append(event)
        plugins_info.append(
            {
                "name": manifest.get("name", name),
                "version": manifest.get("version", "?"),
                "priority": manifest.get("priority", 50),
                "loaded": True,
                "hooks": sorted(set(hooks)),
            }
        )
    plugins_info.sort(key=lambda p: p["priority"])
    return render_template("admin/debug_plugins.html", plugins=plugins_info)
