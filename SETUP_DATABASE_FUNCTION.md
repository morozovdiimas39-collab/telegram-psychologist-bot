# Функция setup-database для публикации

## Как опубликовать функцию

1. Открой [Yandex Cloud Functions](https://console.cloud.yandex.ru/functions)
2. Нажми **"Создать функцию"**
3. Заполни:
   - **Имя**: `setup-database`
   - **Описание**: `Автоматическое создание VM с PostgreSQL`
   - **Среда выполнения**: `Python 3.11`
   - **Точка входа**: `index.handler`
   - **Таймаут**: `300 секунд` (5 минут)
   - **Память**: `256 MB`

4. **Код функции**: Скопируй содержимое файла `backend/setup-database/index.py` (см. ниже)

5. **Зависимости**: Добавь в раздел "Зависимости" содержимое `backend/setup-database/requirements.txt`:
   ```
   psycopg2-binary>=2.9.0
   requests>=2.31.0
   cryptography>=41.0.0
   ```

6. **Переменные окружения**:
   - `YANDEX_CLOUD_TOKEN` = твой OAuth токен Yandex Cloud
   - `DATABASE_URL` = опционально (для временной БД, если нужна)

7. **Создай версию функции**

8. **Скопируй URL функции** и добавь в `backend/func2url.json`:
   ```json
   {
     "setup-database": "https://functions.yandexcloud.net/ТВОЙ_ID"
   }
   ```

## Код функции (index.py)

См. файл `backend/setup-database/index.py` - скопируй его полностью.

## Зависимости (requirements.txt)

```
psycopg2-binary>=2.9.0
requests>=2.31.0
cryptography>=41.0.0
```

## Что делает функция

- Создаёт VM `db-server` в Yandex Cloud
- Устанавливает PostgreSQL 14/15 автоматически
- Настраивает публичный доступ (порт 5432)
- Создаёт базу данных `deployer` и пользователя `deployer_user`
- Генерирует безопасный пароль
- Возвращает готовый DATABASE_URL

## После публикации

1. Обнови `func2url.json` с URL функции
2. Перезапусти dev сервер
3. Кнопка "Создать VM с БД" станет активной
4. Нажми кнопку и подожди 2-3 минуты
5. Скопируй DATABASE_URL и добавь его во все функции деплойера
