Система хуков DeepChan

Все плагины взаимодействуют с ядром только через хуки/события.

Подписка на хук

def init_app(app):

    def my_handler(**kwargs):
        print("Событие произошло")

    app.on("core.started", my_handler)

Список хуков

core.started
- Когда: после загрузки всех плагинов.
- Аргументы: app
- Пример: app.on("core.started", lambda **kw: print("Ready"))

http.before_request
- Когда: перед обработкой любого HTTP-запроса.
- Аргументы: request
- Пример: app.on("http.before_request", lambda **kw: print(kw["request"].path))

ui.header_rendering
- Когда: перед рендерингом шапки.
- Аргументы: request
- Возврат: HTML-строка, которая вставится в <header>.
- Пример: app.on("ui.header_rendering", lambda **kw: "<span>Hello</span>")

ui.footer_rendering
- Когда: перед рендерингом подвала.
- Аргументы: request
- Возврат: HTML-строка, которая вставится в <footer>.
- Пример: app.on("ui.footer_rendering", lambda **kw: "<p>Stats</p>")

boards.filter_list
- Когда: перед отображением списка досок.
- Аргументы: boards (список объектов Board, можно мутировать)
- Пример: app.on("boards.filter_list", lambda boards, **kw: boards.clear())

board.opening
- Когда: при открытии страницы доски.
- Аргументы: board
- Пример: app.on("board.opening", lambda **kw: print(kw["board"].short_name))

thread.opening
- Когда: при открытии треда.
- Аргументы: thread, board
- Пример: app.on("thread.opening", lambda **kw: print(kw["thread"].id))

thread.actions
- Когда: при выводе кнопок действий у треда (на странице доски).
- Аргументы: thread
- Возврат: HTML-строка.
- Пример: app.on("thread.actions", lambda **kw: "<button>Pin</button>")

post.actions
- Когда: при выводе кнопок действий у поста.
- Аргументы: post
- Возврат: HTML-строка.
- Пример: app.on("post.actions", lambda **kw: "<button>Report</button>")

posts.before_create
- Когда: перед созданием поста.
- Аргументы: board, thread, form, ip_address, identity_hash
- Пример: app.on("posts.before_create", lambda **kw: print(kw["form"].comment.data))

posts.after_create
- Когда: после создания поста.
- Аргументы: post, board, thread
- Пример: app.on("posts.after_create", lambda **kw: print(kw["post"].id))

posts.before_render
- Когда: перед отображением поста.
- Аргументы: post
- Пример: app.on("posts.before_render", lambda **kw: print(kw["post"].comment))

threads.before_render
- Когда: перед отображением треда.
- Аргументы: thread
- Пример: app.on("threads.before_render", lambda **kw: print(kw["thread"].id))

threads.list_loaded
- Когда: после загрузки списка тредов доски.
- Аргументы: threads (список), board_id
- Пример: app.on("threads.list_loaded", lambda **kw: print(len(kw["threads"])))

thread.moved
- Когда: после переноса треда на другую доску.
- Аргументы: thread, old_board_id, new_board_id
- Пример: app.on("thread.moved", lambda **kw: print(kw["old_board_id"]))

media.before_process
- Когда: перед обработкой файла.
- Аргументы: file, post, board, thread
- Пример: app.on("media.before_process", lambda **kw: print(kw["file"].filename))

media.after_process
- Когда: после обработки файла.
- Аргументы: file (кортеж), post, board, thread
- Пример: app.on("media.after_process", lambda **kw: print(kw["file"][0]))

admin.menu_rendering
- Когда: при рендеринге меню админки.
- Возврат: HTML-строка.
- Пример: app.on("admin.menu_rendering", lambda **kw: "<a href='/admin/stats'>Stats</a>")

content.changed
- Когда: после удаления поста/треда.
- Аргументы: action ("deleted"), post, thread, board
- Пример: app.on("content.changed", lambda **kw: print(kw["action"]))

Рекомендации

- Хуки (on) используются для изменения данных.
- События (emit) используются для уведомлений.
- Плагины не должны:
  - monkeypatch'ить ядро
  - напрямую менять глобальное состояние
  - импортировать другие плагины
  - регистрировать Blueprint вне init_app()
