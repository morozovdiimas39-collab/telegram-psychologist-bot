-- Добавляем поле database_url в deploy_configs для выбора БД для миграций
ALTER TABLE deploy_configs 
ADD COLUMN IF NOT EXISTS database_url TEXT;

COMMENT ON COLUMN deploy_configs.database_url IS 'URL базы данных для миграций (если не указан, используется DATABASE_URL из переменных окружения функции migrate)';
