-- Создаём таблицу для хранения конфигураций деплоя
CREATE TABLE IF NOT EXISTS t_p88674394_telegram_psychologis.deploy_configs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    domain VARCHAR(255) NOT NULL,
    github_repo VARCHAR(255) NOT NULL,
    vm_ip VARCHAR(50) NOT NULL,
    vm_user VARCHAR(100) DEFAULT 'ubuntu',
    vm_ssh_key TEXT NOT NULL,
    vm_webhook_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индекс для быстрого поиска по имени
CREATE INDEX IF NOT EXISTS idx_deploy_configs_name ON t_p88674394_telegram_psychologis.deploy_configs(name);

-- Комментарии
COMMENT ON TABLE t_p88674394_telegram_psychologis.deploy_configs IS 'Конфигурации деплоя: VM, домены, репозитории';
COMMENT ON COLUMN t_p88674394_telegram_psychologis.deploy_configs.name IS 'Название конфига (например: production, staging)';
COMMENT ON COLUMN t_p88674394_telegram_psychologis.deploy_configs.domain IS 'Домен для деплоя';
COMMENT ON COLUMN t_p88674394_telegram_psychologis.deploy_configs.github_repo IS 'GitHub репозиторий (username/repo)';
COMMENT ON COLUMN t_p88674394_telegram_psychologis.deploy_configs.vm_ip IS 'IP адрес VM сервера';
COMMENT ON COLUMN t_p88674394_telegram_psychologis.deploy_configs.vm_ssh_key IS 'Приватный SSH ключ для доступа к VM';
