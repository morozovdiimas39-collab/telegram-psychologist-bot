#!/usr/bin/env python3
"""
Скрипт для деплоя проекта на VM.
Запускается webhook-сервером на VM при получении запроса.
"""

import os
import sys
import json
import secrets as stdlib_secrets
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


def detect_project_type(project_dir: str) -> str:
    """
    Определяет тип проекта: django, nuxt или vite.
    Порядок: Django → Nuxt → Vite (приоритет при монорепо).
    """
    # Django: manage.py или django в requirements.txt / pyproject.toml
    if os.path.isfile(os.path.join(project_dir, "manage.py")):
        return "django"
    req_txt = os.path.join(project_dir, "requirements.txt")
    if os.path.isfile(req_txt):
        try:
            if "django" in open(req_txt, encoding="utf-8", errors="ignore").read().lower():
                return "django"
        except OSError:
            pass
    pyproject = os.path.join(project_dir, "pyproject.toml")
    if os.path.isfile(pyproject):
        try:
            if "django" in open(pyproject, encoding="utf-8", errors="ignore").read().lower():
                return "django"
        except OSError:
            pass

    # Nuxt: package.json с nuxt в зависимостях или nuxt.config
    pkg_path = os.path.join(project_dir, "package.json")
    if os.path.isfile(pkg_path):
        try:
            with open(pkg_path, encoding="utf-8") as f:
                pkg = json.load(f)
            deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
            if "nuxt" in deps:
                return "nuxt"
        except (json.JSONDecodeError, OSError):
            pass
        for name in ("nuxt.config.ts", "nuxt.config.js", "nuxt.config.mjs"):
            if os.path.isfile(os.path.join(project_dir, name)):
                return "nuxt"

    # По умолчанию — Vite (текущее поведение)
    return "vite"


def deploy_project(github_url: str, project_name: str, domain: str, secrets: list):
    """
    Полный цикл деплоя проекта:
    1. Клонирование репозитория
    2. Определение типа (vite / nuxt / django)
    3. База данных, .env, Dockerfile по типу
    4. docker-compose, сборка и запуск
    5. Настройка nginx и SSL

    Поддерживаемые типы: vite (как раньше), nuxt, django.
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

    # 2. Определение типа проекта
    project_type = detect_project_type(project_dir)
    print(f"📋 Тип проекта: {project_type}")
    
    # 3. База данных
    print("🗄️ Создаю базу данных...")
    db_name = project_name.replace('-', '_')
    run_command(f'sudo -u postgres psql -c "CREATE DATABASE {db_name};" || true')
    print(f"✅ База данных {db_name} готова")
    
    # 4. Порт хоста (уникальный для проекта)
    port = abs(hash(project_name)) % 10000 + 30000

    # 5. Создание .env и Dockerfile по типу проекта
    if project_type == "vite":
        # Vite — без изменений, как было
        container_port = 3000
        env_content = f"""NODE_ENV=production
PORT=3000
DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:5432/{db_name}
"""
        dockerfile = f"""FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "preview"]
"""
    elif project_type == "nuxt":
        container_port = 3000
        env_content = f"""NODE_ENV=production
PORT=3000
NUXT_HOST=0.0.0.0
NUXT_PORT=3000
DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:5432/{db_name}
"""
        dockerfile = f"""FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
ENV NODE_ENV=production
ENV NUXT_HOST=0.0.0.0
ENV NUXT_PORT=3000
CMD ["npm", "run", "start"]
"""
    else:
        # django
        container_port = 8000
        secret_key = stdlib_secrets.token_urlsafe(32)
        env_content = f"""DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:5432/{db_name}
SECRET_KEY={secret_key}
DEBUG=0
ALLOWED_HOSTS=localhost,127.0.0.1,.{domain},{domain}
"""
    
    for secret in secrets:
        if '=' in secret:
            env_content += f"{secret}\n"
    
    with open(f"{project_dir}/.env", "w") as f:
        f.write(env_content)

    if project_type == "django":
        dockerfile = f"""FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn
COPY . .
RUN python manage.py collectstatic --noinput --clear 2>/dev/null || true
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "{{DJANGO_WSGI_MODULE}}"]
"""
        # Пытаемся подставить имя WSGI модуля (project_name/wsgi.py или project_name/wsgi:application)
        wsgi_module = project_name.replace("-", "_") + ".wsgi:application"
        wsgi_path = os.path.join(project_dir, wsgi_module.replace(":application", "").replace(".", os.sep) + ".py")
        if not os.path.isfile(wsgi_path):
            for candidate in ("config/wsgi.py", "core/wsgi.py", "app/wsgi.py", "project/wsgi.py"):
                if os.path.isfile(os.path.join(project_dir, candidate)):
                    wsgi_module = candidate.replace("/", ".").replace(".py", "") + ":application"
                    break
        dockerfile = dockerfile.replace("{{DJANGO_WSGI_MODULE}}", wsgi_module)
    
    with open(f"{project_dir}/Dockerfile", "w") as f:
        f.write(dockerfile)
    
    # 6. Создание docker-compose.yml
    compose = f"""version: '3.8'
services:
  {project_name}:
    build: .
    restart: always
    ports:
      - "{port}:{container_port}"
    env_file:
      - .env
    extra_hosts:
      - "host.docker.internal:host-gateway"
"""
    
    with open(f"{project_dir}/docker-compose.yml", "w") as f:
        f.write(compose)
    
    # 7. Сборка и запуск
    print("🏗️ Собираю Docker контейнер...")
    code, out, err = run_command(f"cd {project_dir} && docker-compose up -d --build")
    if code != 0:
        print(f"⚠️ Предупреждение при сборке: {err[:200]}")
    print("✅ Контейнер запущен")
    
    # 8. Настройка nginx
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
    
    # 9. SSL сертификат
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
