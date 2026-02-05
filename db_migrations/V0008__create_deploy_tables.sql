-- Таблица для хранения VM серверов
CREATE TABLE IF NOT EXISTS vm_instances (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    ip_address VARCHAR(50) NOT NULL,
    ssh_user VARCHAR(100) DEFAULT 'ubuntu',
    ssh_private_key TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица для конфигураций деплоя
CREATE TABLE IF NOT EXISTS deploy_configs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    domain VARCHAR(255) NOT NULL,
    github_repo VARCHAR(500) NOT NULL,
    vm_instance_id INTEGER REFERENCES vm_instances(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Вставляем дефолтный VM сервер
INSERT INTO vm_instances (name, ip_address, ssh_user, ssh_private_key)
VALUES ('yandex-vm-1', '158.160.115.239', 'ubuntu', 'PLACEHOLDER_SSH_KEY')
ON CONFLICT DO NOTHING;

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_deploy_configs_name ON deploy_configs(name);
CREATE INDEX IF NOT EXISTS idx_vm_instances_ip ON vm_instances(ip_address);
