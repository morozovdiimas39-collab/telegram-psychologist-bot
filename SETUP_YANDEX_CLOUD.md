# Настройка Yandex Cloud: БД и секреты

> **Для деплойера:** См. также [SETUP_DEPLOYER_DATABASE.md](./SETUP_DEPLOYER_DATABASE.md) - специальная инструкция по настройке БД для самого деплойера.

## Что нужно настроить

### 1. База данных PostgreSQL

**Вариант A: Managed PostgreSQL (рекомендуется)**
1. Открой [Yandex Cloud Console](https://console.cloud.yandex.ru/)
2. Перейди в **Managed Service for PostgreSQL**
3. Нажми **"Создать кластер"**
4. Настройки:
   - **Имя**: `rsya-db` (или любое другое)
   - **Версия**: PostgreSQL 14 или 15
   - **Класс хоста**: `s2.micro` (минимальный, ~500₽/мес) или `s2.small` (~1000₽/мес)
   - **Диск**: SSD, 10 GB
   - **База данных**: `rsya_cleaner` (или другое имя)
   - **Пользователь**: `rsya_user`
   - **Пароль**: придумай надёжный пароль (сохрани его!)
   - **Хост**: выбери публичный доступ (Public IP)
5. После создания скопируй **FQDN хоста** (например: `c-xxx.rw.mdb.yandexcloud.net`)
6. **DATABASE_URL** будет выглядеть так:
   ```
   postgresql://rsya_user:ТВОЙ_ПАРОЛЬ@c-xxx.rw.mdb.yandexcloud.net:6432/rsya_cleaner?sslmode=require
   ```

**Вариант B: PostgreSQL на VM (дешевле, но нужно самому администрировать)**
1. Создай VM через деплойер (кнопка "Создать VM")
2. Подключись по SSH: `ssh ubuntu@IP_АДРЕС`
3. Установи PostgreSQL:
   ```bash
   sudo apt-get update
   sudo apt-get install -y postgresql postgresql-contrib
   sudo systemctl start postgresql
   sudo systemctl enable postgresql
   ```
4. Создай БД и пользователя:
   ```bash
   sudo -u postgres psql
   ```
   В psql:
   ```sql
   CREATE DATABASE rsya_cleaner;
   CREATE USER rsya_user WITH PASSWORD 'ТВОЙ_ПАРОЛЬ';
   GRANT ALL PRIVILEGES ON DATABASE rsya_cleaner TO rsya_user;
   \q
   ```
5. Настрой доступ извне:
   ```bash
   sudo nano /etc/postgresql/14/main/postgresql.conf
   # Раскомментируй: listen_addresses = '*'
   
   sudo nano /etc/postgresql/14/main/pg_hba.conf
   # Добавь в конец:
   host    all    all    0.0.0.0/0    md5
   
   sudo systemctl restart postgresql
   sudo ufw allow 5432/tcp
   ```
6. **DATABASE_URL** будет:
   ```
   postgresql://rsya_user:ТВОЙ_ПАРОЛЬ@IP_АДРЕС_VM:5432/rsya_cleaner
   ```

### 2. Секреты для облачных функций

Нужно добавить секреты в каждую функцию. Есть два способа:

#### Способ 1: Через консоль Yandex Cloud (вручную)

Для каждой функции (`deploy-long`, `deploy-functions`, `migrate`, `deploy-config`, `vm-setup`, `vm-list`, `yc-sync`, `deploy-status`):

1. Открой функцию в [Yandex Cloud Console](https://console.cloud.yandex.ru/functions)
2. Перейди в **"Версии"** → выбери последнюю версию → **"Редактировать"**
3. В разделе **"Переменные окружения"** добавь:

   **Для всех функций:**
   - `DATABASE_URL` = `postgresql://rsya_user:ПАРОЛЬ@ХОСТ:ПОРТ/rsya_cleaner?sslmode=require`
   - `MAIN_DB_SCHEMA` = `public` (или оставь пустым)

   **Для функций, которые работают с GitHub:**
   - `GITHUB_TOKEN` = твой GitHub Personal Access Token
     - Как получить: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
     - Права: `repo` (полный доступ к репозиториям)

   **Для функций, которые работают с Yandex Cloud API:**
   - `YANDEX_CLOUD_TOKEN` = OAuth токен Yandex Cloud
     - Как получить: [Yandex Cloud OAuth](https://oauth.yandex.ru/)
     - Разрешения: Cloud Management, Compute, Serverless Functions

4. Сохрани версию

#### Способ 2: Через Yandex Cloud Lockbox (рекомендуется для продакшена)

1. Создай секрет в **Lockbox**:
   - Перейди в **Lockbox** → **Секреты** → **Создать секрет**
   - Добавь все переменные как ключи:
     - `DATABASE_URL`
     - `GITHUB_TOKEN`
     - `YANDEX_CLOUD_TOKEN`
     - `MAIN_DB_SCHEMA`
   - Сохрани секрет

2. Для каждой функции:
   - В настройках версии → **"Сервисный аккаунт"** → создай новый или выбери существующий
   - В **"Переменные окружения"** добавь ссылку на секрет Lockbox

### 3. Какие секреты нужны для каждой функции

| Функция | DATABASE_URL | GITHUB_TOKEN | YANDEX_CLOUD_TOKEN | Другие |
|---------|--------------|--------------|-------------------|---------|
| `deploy-long` | ✅ | ✅ | ❌ | - |
| `deploy-functions` | ❌ | ✅ | ✅ | - |
| `migrate` | ✅ | ✅ | ❌ | - |
| `deploy-config` | ✅ | ❌ | ❌ | - |
| `vm-setup` | ✅ | ❌ | ✅ | - |
| `vm-list` | ✅ | ❌ | ❌ | - |
| `yc-sync` | ✅ | ❌ | ✅ | - |
| `deploy-status` | ✅ | ❌ | ❌ | - |
| `vm-ssh-key` | ✅ | ❌ | ❌ | Получение SSH ключа для VM |

### 4. Быстрая проверка

После настройки проверь:

1. **БД доступна:**
   ```bash
   psql "postgresql://rsya_user:ПАРОЛЬ@ХОСТ:ПОРТ/rsya_cleaner?sslmode=require"
   ```

2. **Функции работают:**
   - В деплойере нажми "Применить миграции БД" → должна создаться таблица `schema_migrations`
   - Нажми "Деплой backend-функций" → должно работать без ошибок

### 5. Применение миграций

После создания БД и настройки секретов:

1. В деплойере выбери конфиг с твоим `github_repo`
2. Нажми **"Применить миграции БД"**
3. Все SQL файлы из `db_migrations/` применятся автоматически

---

## Альтернатива: автоматический скрипт настройки

Если хочешь, я могу создать Python скрипт, который:
- Создаст Managed PostgreSQL через API
- Настроит все секреты в функциях автоматически
- Применит миграции

Нужен такой скрипт?
