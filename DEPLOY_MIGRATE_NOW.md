# Как обновить функцию migrate (без ZIP)

502 Bad Gateway означает, что в облаке всё ещё старая версия функции. Нужно задеплоить новый код.

## Вариант 1: Через GitHub (если есть yc или деплой-функции)

1. Запушь код в GitHub:
   ```bash
   git add backend/migrate/
   git commit -m "migrate: GET + github_repo, без ZIP"
   git push
   ```

2. На странице Deploy → «Деплой backend-функций» → запусти деплой с репозиторием твоего проекта

## Вариант 2: Вручную в Yandex Cloud Console

1. Открой https://console.cloud.yandex.ru/functions
2. Найди функцию **migrate** (или по URL с ID `d4eoo7gt252g039lr5bj`)
3. Вкладка **«Редактор»** → скопируй весь код из `backend/migrate/index.py`
4. В `requirements.txt` должно быть:
   ```
   psycopg2-binary>=2.9.0
   requests>=2.28.0
   ```
5. **«Создать версию»**

## Вариант 3: Через yc CLI (если установлен)

```bash
./scripts/deploy-migrate-only.sh
```

## После деплоя

Проверь на странице Deploy: «Применить миграции БД»
