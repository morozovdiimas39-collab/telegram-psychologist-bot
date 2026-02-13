"""
Отдельная функция для установки SSL (certbot) на VM.
Вызывается кнопкой «Установить SSL» в деплойере.
"""
import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import paramiko
from io import StringIO

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Max-Age': '86400',
}


def handler(event: dict, context) -> dict:
    method = (event.get('httpMethod') or event.get('requestMethod') or 'POST').upper()
    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': '', 'isBase64Encoded': False}

    try:
        config_name = None
        # GET: config_name из query
        params = event.get('queryStringParameters') or event.get('params') or {}
        if isinstance(params, dict):
            config_name = params.get('config_name')
            if isinstance(config_name, list):
                config_name = config_name[0] if config_name else None
        # POST: из body
        if not config_name:
            body_str = event.get('body', '{}') or '{}'
            body = json.loads(body_str) if isinstance(body_str, str) else body_str
            config_name = body.get('config_name')

        if not config_name:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', **CORS_HEADERS},
                'body': json.dumps({'error': 'Укажи config_name'}),
                'isBase64Encoded': False
            }

        dsn = os.environ.get('DATABASE_URL')
        if not dsn:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', **CORS_HEADERS},
                'body': json.dumps({'error': 'DATABASE_URL не настроен'}),
                'isBase64Encoded': False
            }

        schema = os.environ.get('MAIN_DB_SCHEMA', 'public')
        conn = psycopg2.connect(dsn)
        conn.autocommit = True
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            f"""
            SELECT dc.domain, vm.ip_address, vm.ssh_user, vm.ssh_private_key
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
                'headers': {'Content-Type': 'application/json', **CORS_HEADERS},
                'body': json.dumps({'error': f'Конфиг {config_name} не найден'}),
                'isBase64Encoded': False
            }

        vm_ip = config['ip_address']
        domain = config['domain']
        ssh_user = config['ssh_user'] or 'ubuntu'
        ssh_key = config['ssh_private_key']

        if not vm_ip or not ssh_key:
            logs = ["❌ VM не привязана или нет SSH ключа в БД"]
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', **CORS_HEADERS},
                'body': json.dumps({'error': 'Нет VM или SSH ключа', 'logs': logs}),
                'isBase64Encoded': False
            }

        logs = [
            f"🔒 Установка SSL для {domain}",
            f"🖥️ Сервер: {vm_ip}",
            "",
            "🔐 Подключаюсь по SSH..."
        ]

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            pkey = paramiko.RSAKey.from_private_key(StringIO(ssh_key))
        except Exception as e:
            logs.append(f"❌ Ошибка SSH ключа: {e}")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', **CORS_HEADERS},
                'body': json.dumps({'error': str(e), 'logs': logs}),
                'isBase64Encoded': False
            }

        ssh.connect(hostname=vm_ip, username=ssh_user, pkey=pkey, timeout=30, allow_agent=False, look_for_keys=False)
        logs.append("✅ SSH подключение установлено")
        logs.append("")

        # Certbot
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
            for line in certbot_out.strip().split('\n')[-12:]:
                logs.append(f"   {line}")
            if 'could not resolve' in certbot_out.lower() or 'dns' in certbot_out.lower():
                logs.append("")
                logs.append(f"⚠️ Настрой DNS A-запись: {domain} → {vm_ip}")

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', **CORS_HEADERS},
            'body': json.dumps({'success': True, 'logs': logs, 'url': f"https://{domain}"}),
            'isBase64Encoded': False
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', **CORS_HEADERS},
            'body': json.dumps({'error': str(e)}),
            'isBase64Encoded': False
        }
