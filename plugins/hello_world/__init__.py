import logging

log = logging.getLogger(__name__)


def init_app(app):
    """Вызывается ядром при инициализации плагина."""

    def on_core_started(**kwargs):
        log.info("Hello from the hello_world plugin! DeepChan has started.")

    # Подписываемся на событие старта ядра
    app.on("core.started", on_core_started)

    # Пример: как в будущем добавить виджет в подвал
    # def on_footer_render(**kwargs):
    #     return "<p>Hello, World!</p>"
    # app.on('ui.footer_rendering', on_footer_render)
