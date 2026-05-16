from flask import current_app, g, redirect, request, url_for

from services.preferences import get_preference, set_preference


def init_app(app):
    @app.before_request
    def apply_language():
        identity = getattr(g, "identity", {})
        if identity and identity.get("id"):
            lang = get_preference(identity["id"], "language")
            if lang and "SETTINGS" in current_app.config:
                current_app.config["SETTINGS"]._cache["SITE_LANG"] = lang

    def footer_widget(**kwargs):
        identity = getattr(g, "identity", {})
        if not identity or not identity.get("id"):
            return ""
        lang = get_preference(identity["id"], "language") or "ru"
        ru_sel = "selected" if lang == "ru" else ""
        en_sel = "selected" if lang == "en" else ""
        return (
            '<div style="text-align:center; margin-top:10px;">'
            '<form method="post" action="/set-language" style="display: inline;">'
            f'<select name="language" onchange="this.form.submit()">'
            f'<option value="ru" {ru_sel}>RU</option>'
            f'<option value="en" {en_sel}>EN</option>'
            "</select>"
            '<noscript><input type="submit" value="Go"></noscript>'
            "</form>"
            "</div>"
        )

    app.on("ui.footer_rendering", footer_widget)

    @app.route("/set-language", methods=["POST"])
    def set_language():
        identity = getattr(g, "identity", {})
        if identity and identity.get("id"):
            lang = request.form.get("language", "ru")
            set_preference(identity["id"], "language", lang)
            if "SETTINGS" in current_app.config:
                current_app.config["SETTINGS"]._cache["SITE_LANG"] = lang
        return redirect(request.referrer or url_for("main.index"))
