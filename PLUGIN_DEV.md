# Разработка плагинов DeepChan

Плагины располагаются в:

```text
plugins/<plugin_name>/
```

---

# Структура плагина

```text
plugins/
└── my_plugin/
    ├── plugin.json
    └── __init__.py
```

---

## plugin.json

```json
{
  "name": "My Plugin",
  "version": "1.0.0",
  "description": "Описание плагина",
  "api_version": 1,
  "priority": 50
}
```

---

## Приоритет загрузки

Чем меньше число — тем раньше загружается плагин.

---

# init_app(app)

Каждый плагин обязан экспортировать функцию:

```python
def init_app(app):
    pass
```

Через неё:

- регистрируются hooks
- подключаются Blueprint
- добавляются UI-элементы

---

# Blueprint

Рекомендуется использовать отдельный namespace:

```python
bp = Blueprint(
    "my_plugin",
    __name__,
    url_prefix="/plugins/my_plugin"
)
```

---

# Пример плагина

```python
from flask import Blueprint

bp = Blueprint(
    "hello_plugin",
    __name__,
    url_prefix="/plugins/hello"
)

def init_app(app):

    @app.on("core.started")
    def started(**kwargs):
        print("Plugin loaded")

    app.register_blueprint(bp)
```

---

# Рекомендации

## Не делать

- регистрацию Blueprint на import
- SQL-запросы внутри UI hooks
- render_template_string внутри rendering hooks
- импорт других плагинов

---

## Делать

- использовать service layer
- подписываться на hooks/events
- держать плагины изолированными
- использовать context

---

# Shared entities

Для доступа к сущностям используйте сервисы:

```python
from services.boards import get_boards
from services.posts import get_post
```

Не рекомендуется:

```python
Board.query.all()
```

внутри плагинов.
