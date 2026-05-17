# Changelog

Все заметные изменения проекта документируются в этом файле.

Формат основан на:
- Keep a Changelog
- Semantic Versioning

---

# [1.2.11] — 2026-05-17

# Добавлено
- Identity-сервис и транспортная идентификация (I2P X-I2P-DestB32/DestHash)
- Сервис доверия (trust_service) для подсчёта trust_score
- Identity-based капча
- Теневой бан (плагин shadow_ban)
- Быстрые админские кнопки (плагин admin_quick_actions): удаление тредов/постов, теневой бан, включение по identity
- Миграция: поле identity_hash в таблицах post, ban, report
- Замена IP на identity_hash в check_ban, check_rate_limit

# Изменено
- Система полностью перешла на identity-based идентификацию вместо IP
- Плагин language_selector теперь использует identity для сохранения выбора языка
- Улучшена безопасность CSRF-токенов для плагинов
- В шаблоны добавлены точки вставки для хуков thread.actions и post.actions

# Исправлено
- Ошибки импорта g в сервисах posts.py и security.py
- CSRF token invalid при отключении быстрых кнопок
- Отсутствие кнопок действий в интерфейсе

---

# [1.2.10] — 2026-05-16

## Добавлено
- Таблица user_preferences для хранения настроек
- Сервис services/preferences.py (get_preference, set_preference)
- Плагин i2p_identity: создает легковесную identity на основе X-I2P-DestB32/DestHash sha256(destb32 + secret_key)
- Плагин language_selector: персональный выбор языка с сохранением в БД и автоматическим применением
- Отладочная страница /admin/debug/plugins

## Изменено
- Применение языка теперь корректно переопределяет глобальную настройку и восстанавливает её после запроса
- Плагин language_selector использует компактный селект, не сливается со статистикой

## Исправлено
- Рекурсия в хуке ui.header_rendering (полностью исключен render_template_string)
- Отсутствие отступа в app.py для debug блюпринта

---

# [1.2.9] — 2026-05-15

## Добавлено

- Service Layer:
  - `services/boards.py`
  - `services/posts.py`
  - `services/threads.py`
  - `services/media.py`
- Новые hooks/events для постов, тредов и медиа
- Плагин скрытия досок
- Расширение админского меню через hooks

## Изменено

- Переход к plugin-oriented архитектуре
- Централизация доступа к shared entities

## Исправлено

- Конфликты плагинов при фильтрации досок
- Двойная регистрация Blueprint
- RecursionError при render hooks

---

# [1.2.1] — 2026-05-12

## Добавлено

- Полная i18n-система
- Поддержка:
  - русского
  - английского
  - немецкого
  - французского
- CSP-заголовки
- Автоочистка `post_fts`

## Изменено

- Улучшено кеширование
- Обновлён install.sh
- Обновлён pre-commit

## Исправлено

- Потеря формы при ошибке captcha
- CSRF-проблемы в админке
- Ошибки локализации
