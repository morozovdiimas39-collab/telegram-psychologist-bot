import json
import os
import requests
import base64
import subprocess
import tempfile
from pathlib import Path


def handler(event: dict, context) -> dict:
    """Полный деплой фронтенда: билд проекта + загрузка на VM + настройка Nginx + SSL"""
    method = event.get('httpMethod', 'POST')

    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': '',
            'isBase64Encoded': False
        }

    try:
        body = json.loads(event.get('body', '{}'))
        domain = body.get('domain', '').strip()
        github_repo = body.get('github_repo', '').strip()
        
        vm_ip = os.environ.get('VM_IP_ADDRESS')
        vm_user = os.environ.get('VM_USER', 'ubuntu')
        ssh_key = os.environ.get('VM_SSH_KEY')
        github_token = os.environ.get('GITHUB_TOKEN')
        
        logs = []
        
        if not domain or not github_repo:
            raise ValueError("domain и github_repo обязательны")
        
        if not vm_ip or not ssh_key:
            raise ValueError("VM_IP_ADDRESS и VM_SSH_KEY должны быть в секретах")
        
        logs.append(f"🎨 Начинаю деплой фронтенда для {domain}")
        logs.append(f"📦 Репозиторий: {github_repo}")
        logs.append(f"🖥️ VM: {vm_ip}")
        
        # 1. Клонируем репозиторий
        logs.append("")
        logs.append("📥 Клонирую репозиторий из GitHub...")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            clone_url = f"https://{github_token}@github.com/{github_repo}.git" if github_token else f"https://github.com/{github_repo}.git"
            
            result = subprocess.run(
                ['git', 'clone', '--depth', '1', clone_url, tmpdir],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                raise ValueError(f"Ошибка клонирования: {result.stderr}")
            
            logs.append("✅ Репозиторий склонирован")
            
            # 2. Устанавливаем зависимости и билдим
            logs.append("")
            logs.append("📦 Устанавливаю зависимости...")
            
            result = subprocess.run(
                ['bun', 'install'],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                raise ValueError(f"Ошибка установки зависимостей: {result.stderr}")
            
            logs.append("✅ Зависимости установлены")
            logs.append("")
            logs.append("🔨 Билдю проект...")
            
            result = subprocess.run(
                ['bun', 'run', 'build'],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=180
            )
            
            if result.returncode != 0:
                raise ValueError(f"Ошибка билда: {result.stderr}")
            
            logs.append("✅ Проект собран")
            
            # 3. Загружаем на VM
            logs.append("")
            logs.append("📤 Загружаю на VM...")
            
            # Сохраняем SSH ключ
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as key_file:
                key_file.write(ssh_key)
                key_path = key_file.name
            
            os.chmod(key_path, 0o600)
            
            try:
                # Создаём директорию на VM
                project_dir = f"/var/www/{domain}"
                
                subprocess.run(
                    ['ssh', '-i', key_path, '-o', 'StrictHostKeyChecking=no',
                     f"{vm_user}@{vm_ip}",
                     f"sudo mkdir -p {project_dir} && sudo chown {vm_user}:{vm_user} {project_dir}"],
                    check=True,
                    timeout=30
                )
                
                # Загружаем dist
                dist_path = Path(tmpdir) / 'dist'
                if not dist_path.exists():
                    raise ValueError("Папка dist не найдена после билда")
                
                result = subprocess.run(
                    ['rsync', '-avz', '-e', f'ssh -i {key_path} -o StrictHostKeyChecking=no',
                     f"{dist_path}/", f"{vm_user}@{vm_ip}:{project_dir}/"],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if result.returncode != 0:
                    raise ValueError(f"Ошибка rsync: {result.stderr}")
                
                logs.append("✅ Файлы загружены на VM")
                
                # 4. Настраиваем Nginx
                logs.append("")
                logs.append("⚙️ Настраиваю Nginx...")
                
                nginx_config = f"""server {{
    listen 80;
    server_name {domain};
    
    root {project_dir};
    index index.html;
    
    location / {{
        try_files $uri $uri/ /index.html;
    }}
    
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {{
        expires 1y;
        add_header Cache-Control "public, immutable";
    }}
}}"""
                
                # Записываем конфиг
                subprocess.run(
                    ['ssh', '-i', key_path, '-o', 'StrictHostKeyChecking=no',
                     f"{vm_user}@{vm_ip}",
                     f"echo '{nginx_config}' | sudo tee /etc/nginx/sites-available/{domain}"],
                    check=True,
                    timeout=30
                )
                
                # Активируем конфиг
                subprocess.run(
                    ['ssh', '-i', key_path, '-o', 'StrictHostKeyChecking=no',
                     f"{vm_user}@{vm_ip}",
                     f"sudo ln -sf /etc/nginx/sites-available/{domain} /etc/nginx/sites-enabled/ && sudo nginx -t && sudo systemctl reload nginx"],
                    check=True,
                    timeout=30
                )
                
                logs.append("✅ Nginx настроен")
                
                # 5. Устанавливаем SSL
                logs.append("")
                logs.append("🔒 Выпускаю SSL сертификат...")
                
                result = subprocess.run(
                    ['ssh', '-i', key_path, '-o', 'StrictHostKeyChecking=no',
                     f"{vm_user}@{vm_ip}",
                     f"sudo certbot --nginx -d {domain} --non-interactive --agree-tos --email admin@{domain} --redirect"],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if result.returncode == 0:
                    logs.append("✅ SSL сертификат установлен")
                else:
                    logs.append("⚠️ Ошибка SSL - проверь делегирование домена")
                    logs.append(f"   {result.stderr[:200]}")
                
            finally:
                os.unlink(key_path)
        
        logs.append("")
        logs.append(f"🎉 Деплой завершён!")
        logs.append(f"🌐 Сайт доступен: https://{domain}")
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'success': True,
                'logs': logs,
                'url': f"https://{domain}"
            }),
            'isBase64Encoded': False
        }
        
    except subprocess.TimeoutExpired:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': 'Timeout - операция заняла слишком много времени',
                'logs': logs if 'logs' in locals() else []
            }),
            'isBase64Encoded': False
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': str(e),
                'logs': logs if 'logs' in locals() else []
            }),
            'isBase64Encoded': False
        }
