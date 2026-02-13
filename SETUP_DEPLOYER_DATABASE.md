# Настройка базы данных для деплойера

## Проблема
Сейчас деплойер использует БД на `poehali.dev`. Нужно создать свою БД в Yandex Cloud и переключить все функции деплойера на неё.

## Пошаговая инструкция

### Шаг 1: Создай Managed PostgreSQL в Yandex Cloud

1. Открой [Yandex Cloud Console](https://console.cloud.yandex.ru/)
2. Перейди в **Managed Service for PostgreSQL**
3. Нажми **"Создать кластер"**
4. Настройки:
   - **Имя**: `deployer-db` (или любое другое)
   - **Версия**: PostgreSQL 14 или 15
   - **Класс хоста**: `s2.micro` (минимальный, ~500₽/мес)
   - **Диск**: SSD, 10 GB
   - **База данных**: `deployer` (или `deployer_db`)
   - **Пользователь**: `deployer_user`
   - **Пароль**: придумай надёжный пароль (сохрани его!)
   - **Хост**: включи публичный доступ (Public IP)
5. Нажми **"Создать"** и подожди 5-10 минут
6. После создания скопируй **FQDN хоста** (например: `c-xxx.rw.mdb.yandexcloud.net`)

### Шаг 2: Получи DATABASE_URL

Формат будет такой:
```
postgresql://deployer_user:ТВОЙ_ПАРОЛЬ@c-xxx.rw.mdb.yandexcloud.net:6432/deployer?sslmode=require
```

**Важно:** Сохрани этот URL - он понадобится для всех функций деплойера!

### Шаг 3: Примени миграции БД

В деплойере есть папка `db_migrations/` с SQL миграциями. Нужно применить их к новой БД.

#### Вариант A: Через функцию migrate (проще)

1. **Сначала задеплой функцию `migrate`** (если ещё не задеплоена):
   - В деплойере добавь конфиг с репозиторием деплойера
   - Нажми "Деплой backend-функций"
   - Дождись деплоя функции `migrate`

2. **Настрой переменные окружения для `migrate`:**
   - Открой функцию `migrate` в [Yandex Cloud Console](https://console.cloud.yandex.ru/functions)
   - Версии → последняя версия → Редактировать
   - Переменные окружения:
     - `DATABASE_URL` = твой DATABASE_URL из шага 2
     - `GITHUB_TOKEN` = твой GitHub токен

3. **Примени миграции:**
   - В деплойере выбери конфиг с репозиторием деплойера
   - Нажми **"Применить миграции БД"**
   - Дождись завершения
   - Все таблицы будут созданы автоматически

#### Вариант B: Вручную через psql

Если функция migrate ещё не работает:

1. Подключись к БД:
   ```bash
   psql "postgresql://deployer_user:ПАРОЛЬ@c-xxx.rw.mdb.yandexcloud.net:6432/deployer?sslmode=require"
   ```

2. Примени миграции по порядку:
   ```sql
   -- V0008__create_deploy_tables.sql
   CREATE TABLE IF NOT EXISTS vm_instances (
       id SERIAL PRIMARY KEY,
       name VARCHAR(255) NOT NULL,
       ip_address VARCHAR(50) NOT NULL,
       ssh_user VARCHAR(100) DEFAULT 'ubuntu',
       ssh_private_key TEXT NOT NULL,
       status VARCHAR(50) DEFAULT 'creating',
       yandex_vm_id VARCHAR(255),
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );

   CREATE TABLE IF NOT EXISTS deploy_configs (
       id SERIAL PRIMARY KEY,
       name VARCHAR(255) UNIQUE NOT NULL,
       domain VARCHAR(255) NOT NULL,
       github_repo VARCHAR(500) NOT NULL,
       vm_instance_id INTEGER REFERENCES vm_instances(id),
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );

   CREATE INDEX IF NOT EXISTS idx_deploy_configs_name ON deploy_configs(name);
   CREATE INDEX IF NOT EXISTS idx_vm_instances_ip ON vm_instances(ip_address);
   CREATE INDEX IF NOT EXISTS idx_deploy_configs_vm_instance ON deploy_configs(vm_instance_id);
   ```

3. Или скопируй содержимое всех файлов из `db_migrations/` и выполни их по порядку

### Шаг 4: Обнови переменные окружения во всех функциях деплойера

Для каждой функции нужно добавить `DATABASE_URL`:

| Функция | DATABASE_URL | GITHUB_TOKEN | YANDEX_CLOUD_TOKEN | MAIN_DB_SCHEMA |
|---------|--------------|--------------|-------------------|----------------|
| `deploy-config` | ✅ | ❌ | ❌ | `public` (опционально) |
| `deploy-long` | ✅ | ✅ | ❌ | `public` (опционально) |
| `deploy-functions` | ❌ | ✅ | ✅ | - |
| `deploy-status` | ✅ | ❌ | ❌ | `public` (опционально) |
| `vm-setup` | ✅ | ❌ | ✅ | `public` (опционально) |
| `vm-list` | ✅ | ❌ | ❌ | `public` (опционально) |
| `vm-ssh-key` | ✅ | ❌ | ❌ | `public` (опционально) |
| `yc-sync` | ✅ | ❌ | ✅ | `public` (опционально) |
| `migrate` | ✅ | ✅ | ❌ | - |

**Как обновить:**

1. Открой функцию в [Yandex Cloud Console](https://console.cloud.yandex.ru/functions)
2. Версии → последняя версия → Редактировать
3. Переменные окружения → Добавить:
   - `DATABASE_URL` = `postgresql://deployer_user:ПАРОЛЬ@c-xxx.rw.mdb.yandexcloud.net:6432/deployer?sslmode=require`
   - `MAIN_DB_SCHEMA` = `public` (опционально, по умолчанию используется `public`)
4. Сохрани версию

**Повтори для всех функций из таблицы выше!**

### Шаг 5: Проверь работу

1. **Проверь подключение к БД:**
   ```bash
   psql "postgresql://deployer_user:ПАРОЛЬ@c-xxx.rw.mdb.yandexcloud.net:6432/deployer?sslmode=require"
   ```
   
   В psql:
   ```sql
   \dt  -- Покажет все таблицы
   SELECT * FROM vm_instances;  -- Должна быть пустая таблица
   SELECT * FROM deploy_configs;  -- Должна быть пустая таблица
   ```

2. **Проверь функции:**
   - В деплойере попробуй создать VM → должно сохраниться в БД
   - Создай конфиг деплоя → должно сохраниться в БД
   - Проверь что всё работает

## Структура БД деплойера

### Таблица `vm_instances`
Хранит информацию о VM серверах:
- `id` - уникальный ID
- `name` - имя VM
- `ip_address` - IP адрес
- `ssh_user` - пользователь SSH (обычно `ubuntu`)
- `ssh_private_key` - приватный SSH ключ
- `status` - статус (`creating`, `running`, `stopped`, `deleted`)
- `yandex_vm_id` - ID VM в Yandex Cloud
- `created_at`, `updated_at` - временные метки

### Таблица `deploy_configs`
Хранит конфигурации деплоя:
- `id` - уникальный ID
- `name` - название конфига (уникальное)
- `domain` - домен для деплоя
- `github_repo` - GitHub репозиторий
- `vm_instance_id` - ссылка на VM
- `created_at`, `updated_at` - временные метки

## Важно

- ✅ После настройки БД все функции деплойера будут использовать твою БД
- ✅ Данные из старой БД на `poehali.dev` не переносятся автоматически
- ✅ Если нужны старые данные, экспортируй их вручную и импортируй в новую БД
- ✅ Все новые VM и конфиги будут сохраняться в твою БД

## Troubleshooting

### Ошибка подключения к БД

1. Проверь что Managed PostgreSQL имеет публичный доступ
2. Проверь что DATABASE_URL правильный (скопирован полностью)
3. Проверь что пароль правильный
4. Проверь что порт `6432` (для Managed PostgreSQL)

### Таблицы не созданы

1. Проверь что миграции применены (через функцию migrate или вручную)
2. Проверь логи функции migrate в Yandex Cloud Console
3. Попробуй применить миграции вручную через psql

### Функции не работают

1. Проверь что `DATABASE_URL` добавлен во все функции
2. Проверь логи функций в Yandex Cloud Console
3. Убедись что БД доступна из интернета
