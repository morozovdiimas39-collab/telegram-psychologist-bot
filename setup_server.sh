#!/bin/bash
# Скрипт установки PostgreSQL на VM сервере Yandex Cloud

echo "🚀 Установка PostgreSQL..."
sudo apt update
sudo apt install -y postgresql postgresql-contrib

echo "✅ Запуск PostgreSQL..."
sudo systemctl start postgresql
sudo systemctl enable postgresql

echo "📊 Создание базы данных и пользователя..."
sudo -u postgres psql << EOF
CREATE DATABASE deploy_db;
CREATE USER deploy_user WITH PASSWORD 'DeployPass2024!Strong';
GRANT ALL PRIVILEGES ON DATABASE deploy_db TO deploy_user;
\q
EOF

echo "🔓 Настройка удалённого доступа..."
PG_VERSION=$(ls /etc/postgresql/ | head -n 1)
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/$PG_VERSION/main/postgresql.conf
echo "host    all             all             0.0.0.0/0               md5" | sudo tee -a /etc/postgresql/$PG_VERSION/main/pg_hba.conf

echo "🔄 Перезапуск PostgreSQL..."
sudo systemctl restart postgresql

echo "✅ PostgreSQL установлен и настроен!"
echo ""
echo "📋 Данные для подключения:"
echo "DATABASE_URL=postgresql://deploy_user:DeployPass2024!Strong@158.160.115.239:5432/deploy_db"
echo "MAIN_DB_SCHEMA=public"
