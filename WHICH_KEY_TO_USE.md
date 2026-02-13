# Какой ключ использовать для переменных окружения

## Две переменные окружения

### 1. `YANDEX_SERVICE_ACCOUNT_KEY_ID`

**Что использовать:**
- **ID ключа:** `ajeke7hvv73d03siopbo` (это то, что у тебя есть)

**Или (если ID ключа не работает):**
- **ID сервисного аккаунта** (найди в консоли Yandex Cloud)

**Где найти ID сервисного аккаунта:**
1. Открой https://console.cloud.yandex.ru/cloud
2. Перейди: **IAM** → **Сервисные аккаунты**
3. Найди нужный сервисный аккаунт
4. Скопируй его **ID** (длинная строка типа `aje1234567890abcdef`)

---

### 2. `YANDEX_SERVICE_ACCOUNT_PRIVATE_KEY`

**Что использовать:**
Весь твой **приватный ключ** в формате PEM.

**Пример того, как должен выглядеть ключ:**
```
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...
(много строк с данными ключа, обычно 20-30 строк)
...
-----END PRIVATE KEY-----
```

**Важно:**
- ✅ Скопируй **ВЕСЬ блок** от `-----BEGIN PRIVATE KEY-----` до `-----END PRIVATE KEY-----`
- ✅ Включи **все строки** между BEGIN и END
- ✅ Не удаляй переносы строк
- ✅ Не добавляй лишних пробелов в начале/конце

---

## Пример настройки в Yandex Cloud Functions

### Переменная 1:
```
Имя: YANDEX_SERVICE_ACCOUNT_KEY_ID
Значение: ajeke7hvv73d03siopbo
```

### Переменная 2:
```
Имя: YANDEX_SERVICE_ACCOUNT_PRIVATE_KEY
Значение: -----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...
(весь ключ целиком)
...
-----END PRIVATE KEY-----
```

---

## Что делать, если не работает?

### Ошибка 401 (Unauthorized)

Это значит, что **ID ключа не подходит**. Нужно использовать **ID сервисного аккаунта**:

1. Найди ID сервисного аккаунта в консоли (см. выше)
2. Замени значение `YANDEX_SERVICE_ACCOUNT_KEY_ID` на ID сервисного аккаунта
3. Оставь `YANDEX_SERVICE_ACCOUNT_PRIVATE_KEY` без изменений

### Ошибка "Неверный формат приватного ключа"

Проверь:
- ✅ Ключ начинается с `-----BEGIN PRIVATE KEY-----`
- ✅ Ключ заканчивается на `-----END PRIVATE KEY-----`
- ✅ Между BEGIN и END есть много строк с данными
- ✅ Нет лишних пробелов в начале/конце

---

## Итого

**Для `YANDEX_SERVICE_ACCOUNT_KEY_ID`:**
- Сначала попробуй: `ajeke7hvv73d03siopbo` (ID ключа)
- Если не работает: используй ID сервисного аккаунта из консоли

**Для `YANDEX_SERVICE_ACCOUNT_PRIVATE_KEY`:**
- Весь твой приватный ключ (от BEGIN до END, со всеми строками)
