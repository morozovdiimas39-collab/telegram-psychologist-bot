#!/usr/bin/env python3
import json
import os
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List


class DeployHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/deploy':
            self.send_response(404)
            self.end_headers()
            return
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        data = json.loads(body)
        
        github_url = data.get('github_url')
        project_name = data.get('project_name')
        domain = data.get('domain')
        secrets = data.get('secrets', [])
        
        if not all([github_url, project_name, domain]):
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Missing required fields'}).encode())
            return
        
        try:
            result = deploy_project(github_url, project_name, domain, secrets)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")


def deploy_project(github_url: str, project_name: str, domain: str, secrets: List[Dict]) -> Dict:
    deploy_dir = Path(f"/var/www/{project_name}")
    logs = []
    
    logs.append(f"📦 Клонирую {github_url}...")
    if deploy_dir.exists():
        logs.append("♻️ Обновляю существующий репозиторий...")
        subprocess.run(['git', 'pull'], cwd=deploy_dir, check=True)
    else:
        subprocess.run(['git', 'clone', github_url, str(deploy_dir)], check=True)
    logs.append("✅ Репозиторий готов")
    
    logs.append("🔨 Собираю фронтенд...")
    subprocess.run(['npm', 'install'], cwd=deploy_dir, check=True)
    subprocess.run(['npm', 'run', 'build'], cwd=deploy_dir, check=True)
    logs.append("✅ Фронтенд собран")
    
    logs.append("🗄️ Настраиваю PostgreSQL...")
    pg_password = "postgres"
    db_name = f"db_{project_name.replace('-', '_')}"
    subprocess.run([
        'sudo', '-u', 'postgres', 'psql', '-c',
        f"SELECT 'CREATE DATABASE {db_name}' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '{db_name}')\\gexec"
    ], check=True)
    logs.append(f"✅ База данных: {db_name}")
    
    migrations_dir = deploy_dir / 'db_migrations'
    if migrations_dir.exists():
        logs.append("📊 Применяю миграции...")
        for migration_file in sorted(migrations_dir.glob('V*.sql')):
            logs.append(f"  ▸ {migration_file.name}")
            with open(migration_file, 'r') as f:
                sql = f.read()
            subprocess.run(['sudo', '-u', 'postgres', 'psql', '-d', db_name, '-c', sql], check=True)
        logs.append("✅ Миграции применены")
    
    backend_dir = deploy_dir / 'backend'
    if backend_dir.exists():
        logs.append("⚙️ Настраиваю облачные функции...")
        env_file = backend_dir / '.env'
        env_vars = {'DATABASE_URL': f'postgresql://postgres:{pg_password}@localhost/{db_name}'}
        for secret in secrets:
            env_vars[secret['name']] = secret['value']
        with open(env_file, 'w') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
        
        for func_dir in backend_dir.iterdir():
            if func_dir.is_dir() and (func_dir / 'requirements.txt').exists():
                logs.append(f"  ▸ Устанавливаю зависимости для {func_dir.name}")
                subprocess.run(['pip3', 'install', '-r', str(func_dir / 'requirements.txt'), '--target', str(func_dir / 'packages')], check=True)
        
        setup_functions_api(backend_dir, env_vars, logs)
        logs.append("✅ Облачные функции настроены")
    
    logs.append("🌐 Настраиваю Nginx...")
    nginx_config = f"""server {{
    listen 80;
    server_name {domain};
    root /var/www/{project_name}/dist;
    index index.html;
    location / {{
        try_files $uri $uri/ /index.html;
    }}
    location /api/ {{
        proxy_pass http://localhost:5000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}
}}"""
    nginx_site = f"/etc/nginx/sites-available/{project_name}"
    with open(nginx_site, 'w') as f:
        f.write(nginx_config)
    nginx_enabled = f"/etc/nginx/sites-enabled/{project_name}"
    if not os.path.exists(nginx_enabled):
        os.symlink(nginx_site, nginx_enabled)
    subprocess.run(['nginx', '-t'], check=True)
    subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
    logs.append("✅ Nginx настроен")
    logs.append(f"🎉 Деплой завершён! Сайт доступен: http://{domain}")
    return {'success': True, 'logs': logs}


def setup_functions_api(backend_dir: Path, env_vars: Dict, logs: List[str]):
    api_server_code = '''import os, sys, json
from pathlib import Path
from flask import Flask, request, jsonify
app = Flask(__name__)
env_vars = json.loads(os.environ.get("APP_ENV_VARS", "{}"))
for key, value in env_vars.items():
    os.environ[key] = value
functions = {}
backend_dir = Path(__file__).parent
for func_dir in backend_dir.iterdir():
    if func_dir.is_dir() and (func_dir / "index.py").exists():
        func_name = func_dir.name
        sys.path.insert(0, str(func_dir))
        sys.path.insert(0, str(func_dir / "packages"))
        try:
            module = __import__("index")
            functions[func_name] = module.handler
            sys.path.pop(0)
            sys.path.pop(0)
        except Exception as e:
            print(f"Error loading {func_name}: {e}")
@app.route('/api/<function_name>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def call_function(function_name):
    if function_name not in functions:
        return jsonify({'error': 'Function not found'}), 404
    event = {'httpMethod': request.method, 'headers': dict(request.headers), 'queryStringParameters': dict(request.args), 'body': request.get_data(as_text=True), 'isBase64Encoded': False}
    try:
        result = functions[function_name](event, None)
        status = result.get('statusCode', 200)
        headers = result.get('headers', {})
        body = result.get('body', '')
        response = app.make_response(body, status)
        for key, value in headers.items():
            response.headers[key] = value
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)'''
    api_file = backend_dir / 'api_server.py'
    with open(api_file, 'w') as f:
        f.write(api_server_code)
    service_name = f"functions-api-{backend_dir.parent.name}"
    service_file = f"/etc/systemd/system/{service_name}.service"
    service_config = f"""[Unit]
Description=Backend Functions API Server
After=network.target
[Service]
Type=simple
User=www-data
WorkingDirectory={backend_dir}
Environment="APP_ENV_VARS={json.dumps(env_vars)}"
ExecStart=/usr/bin/python3 {api_file}
Restart=always
[Install]
WantedBy=multi-user.target"""
    with open(service_file, 'w') as f:
        f.write(service_config)
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', 'enable', service_name], check=True)
    subprocess.run(['systemctl', 'restart', service_name], check=True)
    logs.append(f"✅ API сервер запущен: {service_name}")


def main():
    port = 9000
    server = HTTPServer(('0.0.0.0', port), DeployHandler)
    print(f"🚀 Deploy webhook server listening on port {port}")
    server.serve_forever()


if __name__ == '__main__':
    main()
