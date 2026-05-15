Разработка плагинов для DeepChan

Плагины — это Python-модули, которые добавляют новую функциональность без изменения ядра.
Они лежат в папке plugins/<имя_плагина>/.

Структура плагина

plugins/
└── my_plugin/
    ├── plugin.json      # Манифест с метаданными
    └── __init__.py      # Код плагина (обязательно)

plugin.json

{
  "name": "My Plugin",
  "version": "1.0.0",
  "description": "Описание плагина",
  "api_version": 1,
  "priority": 50
}

- name — человеческое название (показывается в админке)
- priority — чем МЕНЬШЕ число, тем РАНЬШЕ плагин загружается (по умолчанию 50)

__init__.py

Обязательно должна быть функция init_app(app), через которую плагин подписывается на хуки или регистрирует Blueprint'ы.

def init_app(app):
    # Подписка на хук
    app.on('some_hook', my_handler)

    # Регистрация своего Blueprint (если нужен веб-интерфейс)
    from flask import Blueprint
    bp = Blueprint('my_plugin', __name__, url_prefix='/admin')
    # ... определение маршрутов ...
    app.register_blueprint(bp)

Доступные хуки

См. актуальный список в файле HOOKS.md.

Пример: добавление виджета в подвал

def init_app(app):
    def on_footer_render(**kwargs):
        return '<p>Привет из плагина!</p>'
    app.on('ui.footer_rendering', on_footer_render)

Пример: реакция на создание поста

def init_app(app):
    def on_post_created(post, board, thread, **kwargs):
        app.logger.info(f'Новый пост #{post.id} в /{board.short_name}/')
    app.on('posts.after_create', on_post_created)

Пример: добавление пункта в меню админки

def init_app(app):
    def menu_item(**kwargs):
        return '<a href="/admin/my_page">Моя страница</a> |'
    app.on('admin.menu_rendering', menu_item)

Важные правила

- Не обращайтесь к моделям напрямую. Используйте сервисы (например, services.boards.get_boards()).
- Не используйте render_template_string в UI-хуках, чтобы избежать рекурсии. Собирайте HTML вручную.
- Плагины имеют полный доступ к системе. Устанавливайте только проверенные плагины.
- Изменения enable/disable вступают в силу после перезапуска приложения.

Советы

- Смотрите готовые плагины в папке plugins/ как примеры.
- Для добавления статики (CSS/JS) используйте подпапку static/ внутри своего плагина и ссылайтесь на неё через Blueprint.
