import json
import os
import paramiko
from io import StringIO


def handler(event: dict, context) -> dict:
    """Обновить скрипт деплоя на VM через SSH"""
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

    if method != 'POST':
        return {
            'statusCode': 405,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Method not allowed'}),
            'isBase64Encoded': False
        }

    try:
        vm_ip = os.environ.get('VM_IP_ADDRESS')
        ssh_key = os.environ.get('VM_SSH_KEY')
        
        if not vm_ip or not ssh_key:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'VM_IP_ADDRESS or VM_SSH_KEY not configured'}),
                'isBase64Encoded': False
            }
        
        logs = []
        logs.append(f"📡 Подключаюсь к VM {vm_ip}...")
        
        # Подключение по SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        pkey = paramiko.RSAKey.from_private_key(StringIO(ssh_key))
        ssh.connect(vm_ip, username='ubuntu', pkey=pkey, timeout=10)
        
        logs.append("✅ SSH подключение установлено")
        
        # Читаем скрипт деплоя из текущей директории
        script_path = os.path.join(os.path.dirname(__file__), 'deploy_script.py')
        with open(script_path, 'r') as f:
            deploy_script = f.read()
        
        logs.append("📦 Загружаю новый скрипт деплоя...")
        
        # Загружаем скрипт на VM
        sftp = ssh.open_sftp()
        remote_file = sftp.open('/tmp/deploy_server.py', 'w')
        remote_file.write(deploy_script)
        remote_file.close()
        sftp.close()
        
        logs.append("✅ Скрипт загружен")
        
        # Устанавливаем скрипт
        commands = [
            'sudo mv /tmp/deploy_server.py /usr/local/bin/deploy_server.py',
            'sudo chmod +x /usr/local/bin/deploy_server.py',
            'sudo pkill -f deploy_server.py || true',
            'nohup sudo python3 /usr/local/bin/deploy_server.py > /var/log/deploy_server.log 2>&1 &'
        ]
        
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                error = stderr.read().decode()
                logs.append(f"⚠️ Команда: {cmd}")
                logs.append(f"⚠️ Ошибка: {error}")
        
        logs.append("✅ Скрипт деплоя обновлён и запущен")
        logs.append("🎉 VM готова к деплою с поддержкой БД и функций")
        
        ssh.close()
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'success': True, 'logs': logs}),
            'isBase64Encoded': False
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e), 'logs': logs if 'logs' in locals() else []}),
            'isBase64Encoded': False
        }