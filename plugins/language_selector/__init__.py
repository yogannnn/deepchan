import os

from flask import current_app, g, redirect, request, url_for

from services.preferences import get_preference, set_preference


def get_available_languages():
    """Возвращает список кодов языков, для которых есть JSON-файлы в translations/."""
    translations_dir = os.path.join(current_app.root_path, "translations")
    if not os.path.isdir(translations_dir):
        return ["ru"]  # fallback
    langs = []
    for fname in os.listdir(translations_dir):
        if fname.endswith(".json"):
            # убираем расширение .json
            lang_code = fname[:-5]
            langs.append(lang_code)
    return sorted(langs) or ["ru"]


def init_app(app):
    @app.before_request
    def apply_language():
        identity = getattr(g, "identity", {})
        if identity and identity.get("id"):
            lang = get_preference(identity["id"], "language")
            if lang:
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
        current_lang = get_preference(
            identity["id"], "language"
        ) or current_app.config.get("SITE_LANG", "ru")
        available = get_available_languages()
        options = ""
        for lang_code in available:
            selected = "selected" if lang_code == current_lang else ""
            # Отображаем код языка заглавными буквами (RU, EN, DE…)
            label = lang_code.upper()
            options += f'<option value="{lang_code}" {selected}>{label}</option>'
        return (
            '<div style="text-align: right; margin-top: 20px;">'
            '<form method="post" action="/set-language" style="display: inline;">'
            f'<select name="language" style="width: auto; padding: 4px 8px;">{options}</select> '
            '<input type="submit" value="→" style="padding: 4px 12px; width: auto;">'
            "</form>"
            "</div>"
        )

    app.on("ui.footer_rendering", footer_widget)

    @app.route("/set-language", methods=["POST"])
    def set_language():
        identity = getattr(g, "identity", {})
        if identity and identity.get("id"):
            lang = request.form.get("language", "ru")
            # Принимаем только языки, для которых есть файл перевода
            available = get_available_languages()
            if lang in available:
                set_preference(identity["id"], "language", lang)
                current_app.config["SITE_LANG"] = lang
                if "SETTINGS" in current_app.config:
                    current_app.config["SETTINGS"]._cache["SITE_LANG"] = lang
        return redirect(request.referrer or url_for("main.index"))
