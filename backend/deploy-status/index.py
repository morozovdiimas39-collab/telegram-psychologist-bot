import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import paramiko
from io import StringIO


def handler(event: dict, context) -> dict:
    """Проверить статус деплоя на сервере"""
    method = event.get('httpMethod', 'GET')

    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': '',
            'isBase64Encoded': False
        }

    try:
        query_params = event.get('queryStringParameters') or {}
        config_name = query_params.get('config_name')
        
        if not config_name:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Укажи config_name'}),
                'isBase64Encoded': False
            }
        
        dsn = os.environ['DATABASE_URL']
        schema = os.environ.get('MAIN_DB_SCHEMA', 'public')
        
        conn = psycopg2.connect(dsn)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Получаем конфигурацию
        cur.execute(
            f"""
            SELECT dc.domain, vm.ip_address, vm.ssh_user, vm.ssh_private_key
            FROM {schema}.deploy_configs dc
            JOIN {schema}.vm_instances vm ON dc.vm_instance_id = vm.id
            WHERE dc.name = %s
            """,
            (config_name,)
        )
        
        config = cur.fetchone()
        if not config:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Конфигурация не найдена'}),
                'isBase64Encoded': False
            }
        
        domain = config['domain']
        vm_ip = config['ip_address']
        ssh_user = config['ssh_user']
        ssh_key = config['ssh_private_key']
        
        # Подключаемся по SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        pkey = paramiko.RSAKey.from_private_key(StringIO(ssh_key))
        ssh.connect(
            hostname=vm_ip,
            username=ssh_user,
            pkey=pkey,
            timeout=10,
            allow_agent=False,
            look_for_keys=False
        )
        
        result = {}
        
        # Проверяем логи деплоя
        log_file = f"/tmp/deploy_{domain}.log"
        stdin, stdout, stderr = ssh.exec_command(f"tail -20 {log_file} 2>/dev/null || echo 'Лог не найден'")
        result['deploy_log'] = stdout.read().decode('utf-8')
        
        # Проверяем существует ли проект
        project_dir = f"/var/www/{domain}"
        stdin, stdout, stderr = ssh.exec_command(f"ls -la {project_dir} 2>/dev/null || echo 'Директория не найдена'")
        result['project_dir'] = stdout.read().decode('utf-8')
        
        # Проверяем dist
        stdin, stdout, stderr = ssh.exec_command(f"ls -la {project_dir}/dist 2>/dev/null || echo 'dist не найден'")
        result['dist_dir'] = stdout.read().decode('utf-8')
        
        # Проверяем html
        stdin, stdout, stderr = ssh.exec_command(f"ls -la /var/www/{domain}/html 2>/dev/null || echo 'html не найден'")
        result['html_dir'] = stdout.read().decode('utf-8')
        
        # Проверяем nginx конфиг
        stdin, stdout, stderr = ssh.exec_command(f"cat /etc/nginx/sites-enabled/{domain} 2>/dev/null || echo 'Конфиг не найден'")
        result['nginx_config'] = stdout.read().decode('utf-8')
        
        # Проверяем процессы npm
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep npm | grep -v grep || echo 'npm процессов нет'")
        result['npm_processes'] = stdout.read().decode('utf-8')
        
        # Проверяем логи nginx
        stdin, stdout, stderr = ssh.exec_command("sudo tail -50 /var/log/nginx/error.log")
        result['nginx_error_log'] = stdout.read().decode('utf-8')
        
        stdin, stdout, stderr = ssh.exec_command("sudo tail -20 /var/log/nginx/access.log")
        result['nginx_access_log'] = stdout.read().decode('utf-8')
        
        # Тест конфига nginx
        stdin, stdout, stderr = ssh.exec_command("sudo nginx -t")
        result['nginx_test'] = stderr.read().decode('utf-8')
        
        ssh.close()
        cur.close()
        conn.close()
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps(result),
            'isBase64Encoded': False
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)}),
            'isBase64Encoded': False
        }