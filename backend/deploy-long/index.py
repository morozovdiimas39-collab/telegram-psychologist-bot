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
        if not body_str or body_str.strip() == '':
            body_str = '{}'
        body = json.loads(body_str) if isinstance(body_str, str) else body_str
        
        config_name = body.get('config_name')
        action = body.get('action', 'deploy')  # 'deploy' | 'setup_ssl'
        
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
        
        from io import StringIO
        try:
            pkey = paramiko.RSAKey.from_private_key(StringIO(ssh_key))
        except Exception as key_error:
            logs.append(f"❌ Ошибка парсинга SSH ключа: {str(key_error)}")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Invalid SSH key format', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        ssh.connect(
            hostname=vm_ip,
            username=ssh_user,
            pkey=pkey,
            timeout=30,
            allow_agent=False,
            look_for_keys=False
        )
        
        logs.append("✅ SSH подключение установлено")
        logs.append("")
        
        # Режим "только SSL" — выпускаем сертификат без деплоя
        if action == 'setup_ssl':
            logs.append("🔒 Режим: только установка SSL")
            logs.append("")
            # Устанавливаем certbot если нет
            stdin, stdout, stderr = ssh.exec_command("which certbot 2>/dev/null || echo ''")
            certbot_path = stdout.read().decode('utf-8').strip()
            if not certbot_path:
                logs.append("📦 Устанавливаю certbot...")
                stdin, stdout, stderr = ssh.exec_command("sudo apt-get update && sudo apt-get install -y certbot python3-certbot-nginx", timeout=120)
                stdout.channel.recv_exit_status()
                logs.append("✅ Certbot установлен")
            logs.append("🔒 Запускаю certbot...")
            certbot_cmd = f"sudo certbot --nginx -d {domain} --non-interactive --agree-tos --email admin@{domain} 2>&1"
            stdin, stdout, stderr = ssh.exec_command(certbot_cmd, timeout=120)
            certbot_out = stdout.read().decode('utf-8')
            ssh.close()
            logs.append("")
            if 'Successfully received certificate' in certbot_out or 'Certificate not yet due for renewal' in certbot_out:
                logs.append("✅ SSL сертификат установлен!")
                logs.append(f"   Сайт: https://{domain}")
            else:
                logs.append("📋 Вывод certbot:")
                for line in certbot_out.strip().split('\n')[-15:]:
                    logs.append(f"   {line}")
                if 'could not resolve' in certbot_out.lower() or 'dns' in certbot_out.lower():
                    logs.append("")
                    logs.append("⚠️ Настрой DNS A-запись: " + domain + " → " + vm_ip)
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'success': True, 'logs': logs, 'url': f"https://{domain}"}),
                'isBase64Encoded': False
            }
        
        project_dir = f"/var/www/{domain}"
        
        # Проверяем и устанавливаем git если нужно
        logs.append("🔍 Проверяю git...")
        stdin, stdout, stderr = ssh.exec_command("which git", timeout=10)
        git_path = stdout.read().decode('utf-8').strip()
        
        if not git_path:
            logs.append("📦 Устанавливаю git...")
            stdin, stdout, stderr = ssh.exec_command("sudo apt-get update && sudo apt-get install -y git", timeout=120)
            exit_code = stdout.channel.recv_exit_status()
            if exit_code != 0:
                logs.append(f"❌ Не удалось установить git: {stderr.read().decode('utf-8')}")
                ssh.close()
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'git installation failed', 'logs': logs}),
                    'isBase64Encoded': False
                }
            logs.append("✅ Git установлен")
        else:
            logs.append(f"✅ Git найден: {git_path}")
        
        logs.append("")
        
        # Клонируем репо
        logs.append("📥 Клонирую репозиторий...")
        
        # Нормализуем github_repo (может быть полный URL или owner/repo)
        if github_repo.startswith('http://') or github_repo.startswith('https://'):
            # Извлекаем owner/repo из полного URL
            import re
            match = re.search(r'github\.com[/:]([^/]+/[^/]+?)(?:\.git)?/?$', github_repo)
            if match:
                github_repo = match.group(1)
            else:
                logs.append(f"⚠️ Не удалось извлечь owner/repo из URL: {github_repo}")
        
        # Убираем .git если есть
        github_repo = github_repo.rstrip('/').rstrip('.git')
        
        clone_url = f"https://{github_token}@github.com/{github_repo}.git" if github_token else f"https://github.com/{github_repo}.git"
        logs.append(f"   Репозиторий: {github_repo}")
        
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
        
        # Создаём скрипт деплоя на сервере (запустим в фоне)
        deploy_script = f"""#!/bin/bash
set -e
cd {project_dir}
echo "📦 npm install..." >> /tmp/deploy_{domain}.log
npm install >> /tmp/deploy_{domain}.log 2>&1
echo "✅ Зависимости установлены" >> /tmp/deploy_{domain}.log
echo "🔨 npm run build..." >> /tmp/deploy_{domain}.log  
npm run build >> /tmp/deploy_{domain}.log 2>&1
echo "✅ Проект собран" >> /tmp/deploy_{domain}.log
echo "📋 Копирую файлы в nginx..." >> /tmp/deploy_{domain}.log
sudo mkdir -p /var/www/{domain}/html
sudo cp -r {project_dir}/dist/* /var/www/{domain}/html/
sudo chown -R www-data:www-data /var/www/{domain}/html
echo "✅ Файлы скопированы" >> /tmp/deploy_{domain}.log
echo "✅ Деплой завершён $(date)" >> /tmp/deploy_{domain}.log
"""
        
        # Загружаем скрипт на сервер через SFTP
        sftp = ssh.open_sftp()
        script_path = f"/tmp/deploy_{domain.replace('.', '_')}.sh"
        with sftp.file(script_path, 'w') as f:
            f.write(deploy_script)
        sftp.close()
        
        # Делаем скрипт исполняемым
        ssh.exec_command(f"chmod +x {script_path}")
        
        # Запускаем в фоне (nohup)
        logs.append("🚀 Запускаю npm install + build в фоновом режиме...")
        ssh.exec_command(f"nohup bash {script_path} > /dev/null 2>&1 &")
        time.sleep(1)  # Даём секунду на старт
        
        logs.append("✅ Деплой запущен!")
        logs.append(f"📝 Логи: tail -f /tmp/deploy_{domain}.log")
        logs.append("")
        logs.append("⏳ Сборка займёт 2-3 минуты в фоне")
        logs.append("")
        
        # Настраиваем nginx для поддержки нескольких доменов на одном сервере
        logs.append("⚙️ Настраиваю nginx для домена...")
        
        # Экранируем домен для использования в имени файла
        domain_safe = domain.replace('.', '_').replace('*', '_')
        
        nginx_config = f"""server {{
    listen 80;
    server_name {domain};
    root /var/www/{domain}/html;
    index index.html;
    
    # Логи для этого домена
    access_log /var/log/nginx/{domain_safe}_access.log;
    error_log /var/log/nginx/{domain_safe}_error.log;
    
    location / {{
        try_files $uri $uri/ /index.html =404;
    }}
    
    location ~* \\.(?:css|js|jpg|jpeg|gif|png|ico|svg|woff|woff2|ttf|eot)$ {{
        expires 1y;
        access_log off;
        add_header Cache-Control "public, immutable";
    }}
}}"""
        
        # Создаём конфиг для этого домена
        stdin, stdout, stderr = ssh.exec_command(f"echo '{nginx_config}' | sudo tee /etc/nginx/sites-available/{domain_safe}")
        stdout.channel.recv_exit_status()
        
        # Активируем конфиг (создаём симлинк)
        stdin, stdout, stderr = ssh.exec_command(f"sudo ln -sf /etc/nginx/sites-available/{domain_safe} /etc/nginx/sites-enabled/{domain_safe}")
        stdout.channel.recv_exit_status()
        
        # Проверяем конфигурацию nginx
        stdin, stdout, stderr = ssh.exec_command("sudo nginx -t")
        exit_code = stdout.channel.recv_exit_status()
        
        if exit_code != 0:
            error = stderr.read().decode('utf-8')
            logs.append(f"❌ nginx config invalid: {error}")
            logs.append("⚠️ Продолжаю деплой, но nginx не перезапущен")
        else:
            stdin, stdout, stderr = ssh.exec_command("sudo systemctl reload nginx")
            reload_exit = stdout.channel.recv_exit_status()
            if reload_exit == 0:
                logs.append(f"✅ nginx настроен для домена {domain}")
                logs.append(f"   Конфиг: /etc/nginx/sites-available/{domain_safe}")
            else:
                logs.append("⚠️ Не удалось перезагрузить nginx, но конфиг создан")
        
        # Пробуем выпустить SSL для домена (если DNS уже настроен)
        logs.append("")
        logs.append("🔒 Запускаю certbot для SSL (если DNS настроен)...")
        certbot_cmd = f"sudo certbot --nginx -d {domain} --non-interactive --agree-tos --email admin@{domain} 2>&1 || true"
        stdin, stdout, stderr = ssh.exec_command(certbot_cmd)
        certbot_out = stdout.read().decode('utf-8')
        if 'Successfully received certificate' in certbot_out or 'Certificate not yet due for renewal' in certbot_out:
            logs.append("✅ SSL сертификат настроен")
        elif 'DNS' in certbot_out or 'resolution' in certbot_out.lower():
            logs.append("⚠️ SSL: сначала настрой DNS A-запись, затем перезапусти деплой")
        else:
            logs.append("⚠️ SSL: certbot не выполнен (настрой DNS и перезапусти деплой)")
        
        # Показываем список всех активных доменов на этом сервере
        logs.append("")
        logs.append("📋 Проверяю все домены на этом сервере...")
        stdin, stdout, stderr = ssh.exec_command("ls -1 /etc/nginx/sites-enabled/ 2>/dev/null | grep -v default || echo ''")
        enabled_sites = stdout.read().decode('utf-8').strip()
        if enabled_sites:
            logs.append(f"   Активные домены: {enabled_sites.replace(chr(10), ', ')}")
        else:
            logs.append("   Активные домены не найдены")
        
        ssh.close()
        
        logs.append("")
        logs.append(f"🎉 Деплой завершён!")
        logs.append(f"   Домен: {domain}")
        logs.append(f"   Сайт: https://{domain} или http://{domain}")
        logs.append(f"   По IP: http://{vm_ip}")
        logs.append("")
        logs.append("💡 Чтобы домен открывался вместо IP:")
        logs.append(f"   1. В панели DNS (где купил домен) добавь A-запись:")
        logs.append(f"      {domain} → {vm_ip}")
        logs.append(f"      www.{domain} → {vm_ip} (если нужен www)")
        logs.append(f"   2. Подожди 5–30 мин. propagation DNS")
        logs.append(f"   3. Перезапусти деплой — SSL выпустится автоматически")
        
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