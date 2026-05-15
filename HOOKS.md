# Система хуков DeepChan

Все плагины взаимодействуют с ядром только через hooks/events.

---

## Подписка на хук

```python
def init_app(app):

    def my_handler(**kwargs):
        print("Событие произошло")

    app.on("core.started", my_handler)
```

---

# Основные хуки

## core.started

**Когда:** при старте приложения

**Контекст:**

- `app`

**Использование:**

- запуск фоновых задач
- инициализация
- миграции

---

## http.before_request

**Когда:** перед обработкой HTTP-запроса

**Контекст:**

- `request`

---

## http.after_request

**Когда:** после обработки HTTP-запроса

**Контекст:**

- `request`
- `response`

---

## boards.filter_list

Позволяет изменить список досок перед отображением.

### Пример

```python
def hide_boards(boards, **kwargs):
    boards[:] = [
        b for b in boards
        if b.short_name != "hidden"
    ]
```

---

## posts.before_create

Вызывается перед созданием поста.

### Использование

- антиспам
- wordfilter
- AI-модерация
- watermark

---

## posts.after_create

Вызывается после создания поста.

### Использование

- уведомления
- федерация
- индексация
- логирование

---

## media.before_process

Перед обработкой файла.

---

## media.after_process

После обработки файла.

---

## admin.menu_rendering

Позволяет добавить пункт в админское меню.

---

# Рекомендации

## Hooks

Используются для изменения данных.

Например:

- `boards.filter_list`
- `posts.before_render`

---

## Events

Используются для уведомлений.

Например:

- `posts.created`
- `posts.deleted`

---

# Важно

Плагины не должны:

- monkeypatch'ить ядро
- напрямую менять глобальное состояние
- импортировать другие плагины
- регистрировать Blueprint вне `init_app()`
