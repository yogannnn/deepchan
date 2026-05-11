# Changelog

Все заметные изменения в этом проекте будут задокументированы в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
и проект придерживается [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — 2026-05-11

### Добавлено
- Класс `Settings` (`core/settings.py`) для централизованного управления всеми настройками с правильной типизацией (bool/int/list). Все настройки загружаются из БД и кешируются.
- Полный переход всех модулей на `Settings`: удалены все разрозненные вызовы `current_app.config.get(...)`.
- Pre-commit хуки: `black`, `isort`, кастомная проверка на оставшиеся `config.get`.
- CI/CD (GitHub Actions):
  - `bandit` для статического анализа безопасности (строгий режим, severity >= medium).
  - `pip-audit` для проверки уязвимостей в зависимостях.
  - `CodeQL` для глубокого анализа кода.
  - Автоматическая проверка отсутствия прямых вызовов `config.get`.
- Dependabot сгруппирован по категориям (flask, sqlalchemy, security, other).
- Файл `CHANGELOG.md`.
- Обновлённый `install.sh`, использующий `run_migrations()` и `Settings.DEFAULTS` для согласованности.

### Изменено
- `core/settings.py`: дефолтные значения настроек (`DEFAULTS`) синхронизированы с `install.sh`.
- `conftest.py`: тестовые настройки явно переопределяются через `app.config` для изоляции от `Settings._cache`.
- `blueprints/admin.py`, `blueprints/board.py`, `blueprints/radio.py`, `blueprints/main.py`, `core/middleware.py`, `services/media.py`: все чтения настроек заменены на `current_app.config["SETTINGS"].<свойство>`.
- Удалены неиспользуемые файлы: `core/config.py`, скрипты `migrate_admin_to_settings.sh`, `migrate_board_to_settings.sh`.
- `requirements.txt` обновлён: зафиксированы минимальные безопасные версии пакетов (Flask 3.1.3, Pillow 12.1.1, Werkzeug 3.1.6, requests 2.33.0, waitress 3.0.1, python-dotenv 1.2.2).

### Исправлено
- Ошибка 500 на главной странице, вызванная отсутствием таблицы `board` после тестов.
- Проблема с `IndentationError` в `app.py` при некорректной вставке `setup_logging`.
- Тесты больше не зависят от состояния БД `setting` и корректно отключают капчу через `app.config`.

### Безопасность
- Устранены известные уязвимости в зависимостях (CVE в Flask, Pillow, Werkzeug, requests, waitress, python-dotenv).
- Включён многоуровневый анализ: bandit (паттерны кода), CodeQL (глубокий анализ), pip-audit (зависимости).

## [0.1.0] — 2026-04-21
- Первоначальный публичный релиз.
