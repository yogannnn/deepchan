from flask import current_app, g, redirect, request, url_for

from services.preferences import get_preference, set_preference


def init_app(app):
    @app.before_request
    def apply_language():
        identity = getattr(g, "identity", {})
        if identity and identity.get("id"):
            lang = get_preference(identity["id"], "language")
            if lang:
                # Запоминаем оригинальную глобальную настройку и переопределяем её
                g._original_site_lang = current_app.config.get("SITE_LANG", "ru")
                current_app.config["SITE_LANG"] = lang
                if "SETTINGS" in current_app.config:
                    current_app.config["SETTINGS"]._cache["SITE_LANG"] = lang

    @app.after_request
    def restore_language(response):
        original = g.pop("_original_site_lang", None)
        if original is not None:
            current_app.config["SITE_LANG"] = original
            if "SETTINGS" in current_app.config:
                current_app.config["SETTINGS"]._cache["SITE_LANG"] = original
        return response

    def footer_widget(**kwargs):
        identity = getattr(g, "identity", {})
        if not identity or not identity.get("id"):
            return ""
        lang = get_preference(identity["id"], "language") or "ru"
        ru_sel = "selected" if lang == "ru" else ""
        en_sel = "selected" if lang == "en" else ""
        return (
            '<div style="text-align: right; margin-top: 10px;">'
            '<form method="post" action="/set-language" style="display: inline;">'
            f'<select name="language" style="width: auto; padding: 4px 8px;">'
            f'<option value="ru" {ru_sel}>RU</option>'
            f'<option value="en" {en_sel}>EN</option>'
            "</select> "
            '<input type="submit" value="Сменить язык" style="padding: 4px 12px; width: auto;">'
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
            # Применяем сразу для текущего ответа (после редиректа сработает apply_language)
            current_app.config["SITE_LANG"] = lang
            if "SETTINGS" in current_app.config:
                current_app.config["SETTINGS"]._cache["SITE_LANG"] = lang
        return redirect(request.referrer or url_for("main.index"))
