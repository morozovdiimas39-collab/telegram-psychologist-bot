-- Добавляем поле database_url в deploy_configs для выбора БД для миграций
ALTER TABLE deploy_configs 
ADD COLUMN IF NOT EXISTS database_url TEXT;

-- Добавляем поле database_vm_id для выбора VM с БД из списка существующих VM
ALTER TABLE deploy_configs 
ADD COLUMN IF NOT EXISTS database_vm_id INTEGER REFERENCES vm_instances(id);

COMMENT ON COLUMN deploy_configs.database_url IS 'URL базы данных для миграций (если не указан, используется DATABASE_URL из переменных окружения функции migrate)';
COMMENT ON COLUMN deploy_configs.database_vm_id IS 'ID VM сервера с БД (если указан, database_url формируется автоматически)';
