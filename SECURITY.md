# Политика безопасности DeepChan

## Поддерживаемые версии

| Версия | Поддержка          |
|--------|-------------------|
| 1.1.x  | ✅ Активная        |
| < 1.1  | ❌ Не поддерживается |

## Как сообщить об уязвимости

Если вы нашли уязвимость в безопасности, **пожалуйста, не создавайте публичный Issue**.  
Вместо этого свяжитесь с нами приватно через один из каналов:

- Email: `deepchan@proton.me` (зашифруйте PGP ключом ниже)
- Signal: `+countrycode.number` (заменить на реальный номер)
- Session / Tox / SimpleX: (добавить ID по желанию)

PGP ключ:
```

-----BEGIN PGP PUBLIC KEY BLOCK-----

mDMEafzsHxYJKwYBBAHaRw8BAQdA84MqOsXjnvenzkfyG1MN6WbFn93alroCzxpQ
2ILVtTa0FkRhcmsgPGdhcmxpY0BtYWlsLmkycD6IcgQTFggAGgQLCQgHAhUIAhYB
AhkBBYJp/OwfAp4BApsDAAoJEB3M6RMdpAMgMSAA/RFkjVrM9oG2WA5ELUnmIzqh
UMsLjdOPx/uFXzRr8zJJAP4v5WWUZ8v9bnZ1rmtK8v1MHdLcEF+2LrSiuQTb5FyE
A7g4BGn87B8SCisGAQQBl1UBBQEBB0AbYiJW6+G33BxOqKqcV3zg7WqOhQ/FDCfq
dNf+2KknWgMBCAeIYQQYFggACQWCafzsHwKbDAAKCRAdzOkTHaQDIIB4AP93gJ96
MKN1ARI8fQUiUtwo66fjttv9AZSKMYUDErB1xQD/W9bX3v07QgN0DahZYMjqyzgg
lgciH+xDdN25Z+wFHAQ=
=8B3R
-----END PGP PUBLIC KEY BLOCK-----


```

## Что ожидать

- **Подтверждение:** в течение 48 часов после получения сообщения.
- **Исправление:** критические уязвимости будут исправлены и выпущены в течение 7 дней.
- **Раскрытие:** после выхода исправления вы будете упомянуты в CHANGELOG (по желанию).

Мы ценим ответственное разглашение и будем благодарны за любую помощь в улучшении безопасности DeepChan.

## Безопасность по дизайну

- Полное отсутствие JavaScript.
- Stateless CSRF защита.
- Strict Content-Security-Policy заголовки.
- Автоматический аудит безопасности в CI/CD (CodeQL, bandit, pip-audit).
- Очистка метаданных из загружаемых файлов.
