from flask import current_app, g


def init_app(app):
    @app.before_request
    def select_language():
        identity = getattr(g, "identity", {})
        if identity and identity.get("id"):
            lang = "ru"  # заглушка, позже заменим на lookup
            current_app.logger.info(
                f"Language selector: user {identity['id']} would use {lang}"
            )

    def footer_widget(**kwargs):
        identity = getattr(g, "identity", {})
        if identity and identity.get("id"):
            return '<p style="color:#7ab37a; text-align:center; font-size:0.8rem;">Lang: ru (from identity)</p>'
        return ""

    app.on("ui.footer_rendering", footer_widget)
