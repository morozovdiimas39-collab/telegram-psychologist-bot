# Как задеплоить функцию setup-ssl

Функция **setup-ssl** устанавливает SSL (certbot) на VM. Кнопка «Установить SSL» вызывает её.

## Шаг 1: Создай функцию в Yandex Cloud

1. Открой https://console.cloud.yandex.ru/functions
2. **Создать функцию** → имя: `setup-ssl`
3. Среда: **Python 3.12**

## Шаг 2: Загрузи код

1. Вкладка **«Редактор»**
2. Файл `index.py` — скопируй весь код из `backend/setup-ssl/index.py`
3. Файл `requirements.txt`:
   ```
   psycopg2-binary>=2.9.0
   paramiko>=3.0.0
   ```

## Шаг 3: Переменные окружения

Добавь в настройках функции:
- `DATABASE_URL` — строка подключения к PostgreSQL (та же, что у migrate и deploy-config)
- `MAIN_DB_SCHEMA` — `public` (если не указано, по умолчанию public)

## Шаг 4: Создай версию

Нажми **«Создать версию»**. Скопируй URL функции (например `https://functions.yandexcloud.net/xxxxx`).

## Шаг 5: Добавь URL в проект

Открой `src/lib/setup-ssl-url.ts` и вставь URL:

```ts
export const SETUP_SSL_URL = "https://functions.yandexcloud.net/ТВОЙ_ID";
```

## Шаг 6: Задеплой фронтенд

Нажми «Задеплоить фронтенд» для crode — чтобы новая версия с URL попала на crode.ru.

## Готово

Теперь кнопка «Установить SSL» будет вызывать твою функцию и ставить certbot на сервер.
