-- Таблица для хранения VM инстансов
CREATE TABLE IF NOT EXISTS vm_instances (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    ip_address VARCHAR(50),
    ssh_key TEXT,
    ssh_user VARCHAR(50) DEFAULT 'ubuntu',
    status VARCHAR(50) DEFAULT 'creating',
    yandex_vm_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Добавляем ссылку на VM в deploy_configs
ALTER TABLE deploy_configs 
ADD COLUMN IF NOT EXISTS vm_instance_id INTEGER REFERENCES vm_instances(id);

-- Индекс для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_deploy_configs_vm_instance 
ON deploy_configs(vm_instance_id);