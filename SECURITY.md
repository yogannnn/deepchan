# SECURITY.md

## Поддерживаемые версии

| Версия | Статус |
|---|---|
| 1.2.x | Поддерживается |
| < 1.2 | Не поддерживается |

---

# Сообщение об уязвимостях

Пожалуйста, не публикуйте уязвимости публично до исправления.

## Контакты

- Email: `yogannnn@gmail.com`
- Telegram: `@DeepChanBoard`
- Tox: `B82FA1AB98D895053C3A8A2E27AF200DB35A1480B87BC6676FA1126FE9C5E4785FF927C67465`

---

## PGP

```text
-----BEGIN PGP PUBLIC KEY BLOCK-----
mDMEafzsHxYJKwYBBAHaRw8BAQdA84MqOsXjnvenzkfyG1MN6WbFn93alroCzxpQ
2ILVtTa0FkRhcmsgPGdhcmxpY0BtYWlsLmkycD6IcgQTFggAGgQLCQgHAhUIAhYB
AhkBBYJp/OwfAp4BApsDAAoJEB3M6RMdpAMgMSAA/RFkjVrM9oG2WA5ELUnmIzqh
UMsLjdOPx/uFXzRr8zJJAP4v5WWUZ8v9bnZ1rmtK8v1MHdLcEF+2LrSiuQTb5FyE
-----END PGP PUBLIC KEY BLOCK-----
```

---

# Рекомендации по безопасности

## Администраторам

- используйте i2pd
- обновляйте зависимости
- не отключайте CSP
- используйте HTTPS вне hidden-сетей
- не доверяйте сторонним плагинам

---

## Разработчикам плагинов

- не хранить секреты в коде
- не делать SQL напрямую в UI hooks
- избегать render recursion
- использовать service layer
