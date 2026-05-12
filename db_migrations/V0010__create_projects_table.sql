
-- Создаем таблицу проектов
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    status VARCHAR(50) DEFAULT 'active',
    yandex_folder_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица связи проектов с существующими конфигами деплоя
-- Это позволяет не менять существующую таблицу deploy_configs
CREATE TABLE IF NOT EXISTS project_configs_link (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    config_id INTEGER NOT NULL, -- Ссылка на ID из deploy_configs
    resource_type VARCHAR(50) DEFAULT 'deploy_config', -- Тип ресурса
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);
CREATE INDEX IF NOT EXISTS idx_link_project_id ON project_configs_link(project_id);

-- Вставляем базовые проекты для примера
INSERT INTO projects (name, description) VALUES 
('Психолог Бот', 'Основной проект психологического бота'),
('Маркетинг Недвижимость', 'Проекты связанные с квизами по недвижимости');
