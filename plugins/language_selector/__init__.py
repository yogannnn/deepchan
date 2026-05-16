from flask import current_app, g, redirect, render_template_string, request, url_for

from services.preferences import get_preference, set_preference

LANG_SELECT_TEMPLATE = """
<form method="post" action="/set-language" style="display: inline; margin-left: 20px;">
    <select name="language" onchange="this.form.submit()">
        <option value="ru" {ru_selected}>RU</option>
        <option value="en" {en_selected}>EN</option>
    </select>
    <noscript><input type="submit" value="Go"></noscript>
</form>
"""


def init_app(app):
    @app.before_request
    def apply_language():
        identity = getattr(g, "identity", {})
        if identity and identity.get("id"):
            lang = get_preference(identity["id"], "language")
            if lang:
                # Применяем язык через наш центральный Settings
                if "SETTINGS" in current_app.config:
                    current_app.config["SETTINGS"]._cache["SITE_LANG"] = lang

    def header_widget(**kwargs):
        identity = getattr(g, "identity", {})
        if identity and identity.get("id"):
            lang = get_preference(identity["id"], "language") or "ru"
            ru_sel = "selected" if lang == "ru" else ""
            en_sel = "selected" if lang == "en" else ""
            return render_template_string(
                LANG_SELECT_TEMPLATE, ru_selected=ru_sel, en_selected=en_sel
            )
        return ""

    app.on("ui.header_rendering", header_widget)

    @app.route("/set-language", methods=["POST"])
    def set_language():
        identity = getattr(g, "identity", {})
        if identity and identity.get("id"):
            lang = request.form.get("language", "ru")
            set_preference(identity["id"], "language", lang)
            # Мгновенно применяем новый язык
            if "SETTINGS" in current_app.config:
                current_app.config["SETTINGS"]._cache["SITE_LANG"] = lang
        return redirect(request.referrer or url_for("main.index"))
