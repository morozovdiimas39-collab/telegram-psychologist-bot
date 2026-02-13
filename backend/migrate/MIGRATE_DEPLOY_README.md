# Деплой функции migrate (без ZIP)

Функция migrate в Yandex Cloud всё ещё использует старый код, который требует ZIP.

## Вариант 1: Через деплой из приложения

1. **Закоммить и запушь** изменения в GitHub:
   ```bash
   git add backend/migrate/
   git commit -m "migrate: без ZIP, только github_repo"
   git push
   ```

2. На странице **Deploy** → блок **«Деплой backend-функций»**:
   - Укажи репозиторий (например, `username/telegram-psychologist-bot-main-2`)
   - Если есть поле **«Фильтр функций»** — введи `migrate`
   - Запусти деплой

## Вариант 2: Вручную в Yandex Cloud Console

1. Открой [Yandex Cloud Console](https://console.cloud.yandex.ru) → **Cloud Functions** → функция `migrate`
2. Вкладка **«Редактор»** — замени `index.py` на содержимое из `index.py` в этой папке
3. Убедись, что есть `requirements.txt`:
   ```
   psycopg2-binary>=2.9.0
   requests>=2.28.0
   ```
4. Создай новую версию функции

## Переменные окружения (обязательны)

- `DATABASE_URL` — строка подключения к PostgreSQL
- `GITHUB_TOKEN` — токен GitHub (чтение репозиториев)
