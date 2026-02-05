import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import paramiko
import time


def handler(event: dict, context) -> dict:
    """Деплой проекта через SSH - для Яндекс Облака с увеличенным таймаутом"""
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
        body_str = event.get('body', '{}')
        body = json.loads(body_str) if isinstance(body_str, str) else body_str
        
        config_name = body.get('config_name')
        
        if not config_name:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Укажи config_name'}),
                'isBase64Encoded': False
            }
        
        dsn = os.environ['DATABASE_URL']
        schema = os.environ.get('MAIN_DB_SCHEMA', 'public')
        github_token = os.environ.get('GITHUB_TOKEN', '')
        
        conn = psycopg2.connect(dsn)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute(
            f"""
            SELECT dc.*, vm.ip_address, vm.ssh_user, vm.ssh_private_key, vm.name as vm_name
            FROM {schema}.deploy_configs dc
            LEFT JOIN {schema}.vm_instances vm ON dc.vm_instance_id = vm.id
            WHERE dc.name = %s
            """,
            (config_name,)
        )
        
        config = cur.fetchone()
        cur.close()
        conn.close()
        
        if not config:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'Конфиг {config_name} не найден'}),
                'isBase64Encoded': False
            }
        
        logs = [
            f"🚀 Деплой: {config['domain']}",
            f"📦 Репо: {config['github_repo']}",
            ""
        ]
        
        if not config['vm_instance_id'] or not config['ip_address']:
            logs.append("❌ VM не привязана к конфигу")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'VM не привязана', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        vm_ip = config['ip_address']
        domain = config['domain']
        github_repo = config['github_repo']
        ssh_user = config['ssh_user'] or 'ubuntu'
        ssh_key = config['ssh_private_key']
        
        if not ssh_key:
            logs.append("❌ SSH ключ не найден в БД")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'SSH key missing', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        logs.append(f"🖥️  Сервер: {vm_ip}")
        logs.append(f"👤 Пользователь: {ssh_user}")
        logs.append("")
        logs.append("🔐 Подключаюсь по SSH...")
        
        # SSH подключение
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            pkey = paramiko.RSAKey.from_private_key_file(None, password=None, key=ssh_key)
        except:
            from io import StringIO
            pkey = paramiko.RSAKey.from_private_key(StringIO(ssh_key))
        
        ssh.connect(
            hostname=vm_ip,
            username=ssh_user,
            pkey=pkey,
            timeout=10,
            allow_agent=False,
            look_for_keys=False
        )
        
        logs.append("✅ SSH подключение установлено")
        logs.append("")
        
        project_dir = f"/var/www/{domain}"
        
        # Клонируем репо
        logs.append("📥 Клонирую репозиторий...")
        clone_url = f"https://{github_token}@github.com/{github_repo}.git" if github_token else f"https://github.com/{github_repo}.git"
        
        commands = [
            f"sudo rm -rf {project_dir}",
            f"sudo mkdir -p {project_dir}",
            f"sudo chown -R {ssh_user}:{ssh_user} {project_dir}",
            f"git clone {clone_url} {project_dir}",
        ]
        
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
            exit_code = stdout.channel.recv_exit_status()
            if exit_code != 0:
                error = stderr.read().decode('utf-8')
                logs.append(f"❌ Ошибка: {cmd}")
                logs.append(f"   {error}")
                ssh.close()
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': error, 'logs': logs}),
                    'isBase64Encoded': False
                }
        
        logs.append("✅ Репозиторий склонирован")
        logs.append("")
        
        # npm install (долго!)
        logs.append("📦 Устанавливаю зависимости (это займёт ~60 сек)...")
        stdin, stdout, stderr = ssh.exec_command(f"cd {project_dir} && npm install", timeout=180)
        exit_code = stdout.channel.recv_exit_status()
        
        if exit_code != 0:
            error = stderr.read().decode('utf-8')
            logs.append(f"❌ npm install failed: {error}")
            ssh.close()
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'npm install failed', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        logs.append("✅ Зависимости установлены")
        logs.append("")
        
        # npm build
        logs.append("🔨 Собираю проект...")
        stdin, stdout, stderr = ssh.exec_command(f"cd {project_dir} && npm run build", timeout=180)
        exit_code = stdout.channel.recv_exit_status()
        
        if exit_code != 0:
            error = stderr.read().decode('utf-8')
            logs.append(f"❌ npm build failed: {error}")
            ssh.close()
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'npm build failed', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        logs.append("✅ Проект собран")
        logs.append("")
        
        # Настраиваем nginx
        logs.append("⚙️ Настраиваю nginx...")
        nginx_config = f"""server {{
    listen 80;
    server_name {domain};
    root {project_dir}/dist;
    index index.html;
    
    location / {{
        try_files $uri $uri/ /index.html;
    }}
}}"""
        
        stdin, stdout, stderr = ssh.exec_command(f"echo '{nginx_config}' | sudo tee /etc/nginx/sites-available/{domain}")
        stdout.channel.recv_exit_status()
        
        stdin, stdout, stderr = ssh.exec_command(f"sudo ln -sf /etc/nginx/sites-available/{domain} /etc/nginx/sites-enabled/{domain}")
        stdout.channel.recv_exit_status()
        
        stdin, stdout, stderr = ssh.exec_command("sudo nginx -t")
        exit_code = stdout.channel.recv_exit_status()
        
        if exit_code != 0:
            error = stderr.read().decode('utf-8')
            logs.append(f"❌ nginx config invalid: {error}")
        else:
            stdin, stdout, stderr = ssh.exec_command("sudo systemctl reload nginx")
            stdout.channel.recv_exit_status()
            logs.append("✅ nginx настроен и перезапущен")
        
        ssh.close()
        
        logs.append("")
        logs.append(f"🎉 Деплой завершён!")
        logs.append(f"   Сайт доступен: http://{domain}")
        logs.append(f"   Или по IP: http://{vm_ip}")
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'success': True,
                'logs': logs,
                'url': f"http://{domain}",
                'ip_url': f"http://{vm_ip}"
            }),
            'isBase64Encoded': False
        }
        
    except paramiko.SSHException as e:
        logs.append(f"❌ SSH ошибка: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': f'SSH failed: {str(e)}', 'logs': logs}),
            'isBase64Encoded': False
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)}),
            'isBase64Encoded': False
        }
