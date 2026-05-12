# Деплой функций деплойера в Yandex Cloud

## Проблема
Все функции деплойера сейчас работают через `poehali.dev`. Нужно задеплоить их в твой собственный Yandex Cloud.

## Решение

### ⚡ Вариант 1: Через deploy-functions (САМЫЙ ПРОСТОЙ)

**Важно:** Используй `deploy-functions` через `poehali.dev` **ОДИН РАЗ**, чтобы задеплоить все функции деплойера в твой Yandex Cloud.

1. **Добавь конфиг деплоя для самого деплойера:**
   - Открой деплойер: http://localhost:5173/deploy
   - Нажми "Новый конфиг"
   - Заполни:
     - **Название**: `deployer` (или любое другое)
     - **Домен**: `localhost` (не важно для деплоя функций)
     - **GitHub репозиторий**: `твой-username/telegram-psychologist-bot-main-2` (или полный путь к репозиторию деплойера)
   - Сохрани конфиг

2. **Задеплой функции деплойера:**
   - Найди созданный конфиг в списке
   - Нажми **"Деплой backend-функций"**
   - Дождись завершения (может занять несколько минут)
   - Все функции из папки `backend/` будут задеплоены в твой Yandex Cloud
   - `func2url.json` автоматически обновится с новыми URL

3. **Обнови frontend:**
   - Перезапусти dev сервер: останови (Ctrl+C) и запусти снова `npm run dev`
   - Или просто обнови страницу - изменения подтянутся автоматически
   - Теперь все функции будут использовать твои URL из Yandex Cloud

4. **Проверь:**
   - Открой `backend/func2url.json` - все URL должны быть вида `https://functions.yandexcloud.net/...`
   - Попробуй создать VM или выполнить другое действие - должно работать через твои функции

**После этого деплойер полностью перейдёт на твою инфраструктуру!** 🎉

### Вариант 2: Вручную через Yandex Cloud Console

Для каждой функции в папке `backend/`:

1. Открой [Yandex Cloud Functions](https://console.cloud.yandex.ru/functions)
2. Нажми "Создать функцию"
3. Настройки:
   - **Имя**: имя папки (например, `vm-list`, `deploy-config`)
   - **Описание**: опционально
   - **Среда выполнения**: Python 3.11
   - **Точка входа**: `index.handler`
   - **Таймаут**: 30-60 секунд (для `deploy-functions` — 120 сек; для `deploy-long` — **300 сек**, иначе Nuxt/Vite не успеют собраться)
   - **Память**: 128 MB (для `deploy-functions` и `deploy-long` - 256 MB)

4. **Код функции:**
   - Скопируй содержимое `backend/[имя-функции]/index.py`
   - Вставь в редактор кода функции

5. **Зависимости:**
   - Если есть `requirements.txt`, добавь зависимости в раздел "Зависимости"
   - Или создай файл `requirements.txt` в коде функции

6. **Переменные окружения:**
   - `DATABASE_URL` - строка подключения к PostgreSQL
   - `GITHUB_TOKEN` - GitHub Personal Access Token (для функций, работающих с GitHub)
   - `YANDEX_CLOUD_TOKEN` - OAuth токен Yandex Cloud (для функций, работающих с YC API)
   - `MAIN_DB_SCHEMA` - схема БД (опционально, по умолчанию `public`)

7. **Создай версию функции**

8. **Скопируй URL функции** (будет вида `https://functions.yandexcloud.net/...`)

9. **Обнови `backend/func2url.json`:**
   ```json
   {
     "vm-list": "https://functions.yandexcloud.net/ТВОЙ_ID",
     ...
   }
   ```

### Вариант 3: Через Yandex Cloud CLI (yc)

Если у тебя установлен `yc` CLI:

```bash
# Установи yc CLI если нет
# https://cloud.yandex.ru/docs/cli/quickstart

# Авторизуйся
yc init

# Для каждой функции:
cd backend/vm-list
yc serverless function create --name vm-list
yc serverless function version create \
  --function-name vm-list \
  --runtime python311 \
  --entrypoint index.handler \
  --source-path . \
  --memory 128m \
  --execution-timeout 30s \
  --environment DATABASE_URL=...,GITHUB_TOKEN=...
```

## Список функций для деплоя

### Основные функции деплойера:
- ✅ `deploy-config` - управление конфигами деплоя
- ✅ `deploy-long` - деплой фронтенда на VM (долгий процесс)
- ✅ `deploy-functions` - деплой backend функций
- ✅ `deploy-status` - статус деплоя
- ✅ `vm-setup` - создание VM
- ✅ `vm-list` - список VM (GET/DELETE)
- ✅ `vm-ssh-key` - получение SSH ключа VM
- ✅ `yc-sync` - синхронизация VM с Yandex Cloud
- ✅ `migrate` - применение миграций БД

### Дополнительные функции:
- `quiz-api` - API для квизов (если используешь)
- `metrika-goals` - создание целей в Яндекс.Метрике (если используешь)
- `setup-webhook` - настройка webhook (если используешь)
- `deploy` - старая функция деплоя (может быть не нужна)

## Переменные окружения для каждой функции

| Функция | DATABASE_URL | GITHUB_TOKEN | YANDEX_CLOUD_TOKEN | Другие |
|---------|--------------|--------------|-------------------|---------|
| `deploy-config` | ✅ | ❌ | ❌ | - |
| `deploy-long` | ✅ | ✅ | ❌ | - |
| `deploy-functions` | ❌ | ✅ | ✅ | - |
| `deploy-status` | ✅ | ❌ | ❌ | - |
| `vm-setup` | ✅ | ❌ | ✅ | - |
| `vm-list` | ✅ | ❌ | ❌ (для DELETE нужен) | - |
| `vm-ssh-key` | ✅ | ❌ | ❌ | - |
| `yc-sync` | ✅ | ❌ | ✅ | - |
| `migrate` | ✅ | ✅ | ❌ | - |

## После деплоя

1. **Обнови `func2url.json`** с новыми URL
2. **Закоммить и запушь изменения** в GitHub репозиторий деплойера
3. **Перезапусти dev сервер** или пересобери проект
4. **Проверь работу** - все функции должны использовать твои URL

## Важно

- После деплоя всех функций деплойера, `deploy-functions` будет обновлять `func2url.json` автоматически
- Но сам `deploy-functions` должен быть задеплоен вручную или через poehali.dev один раз
- Убедись что все секреты настроены перед деплоем функций
