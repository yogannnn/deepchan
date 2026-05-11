# Политика безопасности DeepChan

## Поддерживаемые версии

| Версия | Поддержка          |
|--------|-------------------|
| 1.1.x  | ✅ Активная        |
| < 1.1  | ❌ Не поддерживается |

## Как сообщить об уязвимости

Если вы нашли уязвимость в безопасности, **пожалуйста, не создавайте публичный Issue**.  
Вместо этого свяжитесь с нами приватно через один из каналов:

- Email: `yogannnn@gmail.com` (зашифруйте PGP ключом ниже)
- Telegram: `@servertronix`
- Tox: `B82FA1AB98D895053C3A8A2E27AF200DB35A1480B87BC6676FA1126FE9C5E4785FF927C67465`

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
