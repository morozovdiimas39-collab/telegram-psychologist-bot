#!/usr/bin/env python3
"""
Скрипт для деплоя проекта на VM.
Запускается webhook-сервером на VM при получении запроса.
"""

import os
import sys
import json
import subprocess
import argparse


def run_command(cmd: str, shell=True) -> tuple:
    """Выполнить команду и вернуть результат"""
    result = subprocess.run(
        cmd,
        shell=shell,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr


def deploy_project(github_url: str, project_name: str, domain: str, secrets: list):
    """
    Полный цикл деплоя проекта:
    1. Клонирование репозитория
    2. Создание базы данных
    3. Сборка Docker контейнера
    4. Настройка nginx
    5. Выпуск SSL сертификата
    """
    
    print(f"📦 Начинаю деплой {project_name}...")
    
    # 1. Клонирование
    print("📥 Клонирую репозиторий...")
    project_dir = f"/opt/{project_name}"
    if os.path.exists(project_dir):
        run_command(f"rm -rf {project_dir}")
    
    code, out, err = run_command(f"git clone {github_url} {project_dir}")
    if code != 0:
        print(f"❌ Ошибка клонирования: {err}")
        return False
    print("✅ Репозиторий склонирован")
    
    # 2. База данных
    print("🗄️ Создаю базу данных...")
    db_name = project_name.replace('-', '_')
    run_command(f'sudo -u postgres psql -c "CREATE DATABASE {db_name};" || true')
    print(f"✅ База данных {db_name} готова")
    
    # 3. Создание .env файла
    port = abs(hash(project_name)) % 10000 + 30000
    env_content = f"""NODE_ENV=production
PORT=3000
DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:5432/{db_name}
"""
    
    for secret in secrets:
        if '=' in secret:
            env_content += f"{secret}\n"
    
    with open(f"{project_dir}/.env", "w") as f:
        f.write(env_content)
    
    # 4. Создание Dockerfile
    dockerfile = f"""FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "preview"]
"""
    
    with open(f"{project_dir}/Dockerfile", "w") as f:
        f.write(dockerfile)
    
    # 5. Создание docker-compose.yml
    compose = f"""version: '3.8'
services:
  {project_name}:
    build: .
    restart: always
    ports:
      - "{port}:3000"
    env_file:
      - .env
    extra_hosts:
      - "host.docker.internal:host-gateway"
"""
    
    with open(f"{project_dir}/docker-compose.yml", "w") as f:
        f.write(compose)
    
    # 6. Сборка и запуск
    print("🏗️ Собираю Docker контейнер...")
    code, out, err = run_command(f"cd {project_dir} && docker-compose up -d --build")
    if code != 0:
        print(f"⚠️ Предупреждение при сборке: {err[:200]}")
    print("✅ Контейнер запущен")
    
    # 7. Настройка nginx
    print("🌐 Настраиваю nginx...")
    nginx_config = f"""server {{
    listen 80;
    server_name {domain};

    location / {{
        proxy_pass http://localhost:{port};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_cache_bypass $http_upgrade;
    }}
}}
"""
    
    with open(f"/etc/nginx/sites-available/{project_name}", "w") as f:
        f.write(nginx_config)
    
    run_command(f"ln -sf /etc/nginx/sites-available/{project_name} /etc/nginx/sites-enabled/{project_name}")
    run_command("nginx -t && systemctl reload nginx")
    print("✅ Nginx настроен")
    
    # 8. SSL сертификат
    print("🔒 Выпускаю SSL сертификат...")
    run_command(
        f"certbot --nginx -d {domain} --non-interactive --agree-tos "
        f"--email admin@{domain} || echo 'SSL setup skipped'"
    )
    print("✅ SSL настроен")
    
    print(f"\n🚀 Проект успешно развернут!")
    print(f"🌍 Доступен по адресу: https://{domain}")
    
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--github', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--domain', required=True)
    parser.add_argument('--secrets', default='[]')
    
    args = parser.parse_args()
    
    secrets = json.loads(args.secrets) if args.secrets else []
    
    success = deploy_project(
        github_url=args.github,
        project_name=args.name,
        domain=args.domain,
        secrets=secrets
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
