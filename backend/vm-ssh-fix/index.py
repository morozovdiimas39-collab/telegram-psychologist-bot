import json
import os
import paramiko
from io import StringIO


def handler(event: dict, context) -> dict:
    """Запустить systemd сервис на VM через SSH"""
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
        vm_ip = os.environ.get('VM_IP_ADDRESS')
        ssh_key_str = os.environ.get('VM_SSH_KEY', '')
        
        logs = []
        logs.append("🔐 Подключаюсь к VM по SSH...")
        
        # Если ключа нет - пытаемся по паролю (Ubuntu default)
        if not ssh_key_str or ssh_key_str == '':
            logs.append("⚠️ SSH ключ не найден, пробую подключение по паролю...")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Пытаемся подключиться без ключа (публичный образ Ubuntu обычно разрешает SSH без аутентификации)
            try:
                ssh.connect(
                    hostname=vm_ip,
                    username='ubuntu',
                    timeout=10,
                    allow_agent=False,
                    look_for_keys=False
                )
            except:
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({
                        'error': 'SSH ключ не настроен. Добавь секрет VM_SSH_KEY с приватным ключом или пересоздай VM с ключом.',
                        'logs': logs
                    }),
                    'isBase64Encoded': False
                }
        else:
            # Создаем SSH клиент
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Загружаем приватный ключ
            key_file = StringIO(ssh_key_str)
            try:
                pkey = paramiko.RSAKey.from_private_key(key_file)
            except:
                key_file.seek(0)
                try:
                    pkey = paramiko.Ed25519Key.from_private_key(key_file)
                except:
                    key_file.seek(0)
                    pkey = paramiko.ECDSAKey.from_private_key(key_file)
            
            # Подключаемся
            ssh.connect(
                hostname=vm_ip,
                username='ubuntu',
                pkey=pkey,
                timeout=10
            )
        
        logs.append("✅ SSH подключение установлено")
        
        # Проверяем статус webhook сервиса
        logs.append("📊 Проверяю статус webhook...")
        stdin, stdout, stderr = ssh.exec_command('sudo systemctl status deploy-webhook')
        status_output = stdout.read().decode('utf-8')
        logs.append(status_output[:500])
        
        # Проверяем логи
        logs.append("")
        logs.append("📋 Логи webhook:")
        stdin, stdout, stderr = ssh.exec_command('sudo journalctl -u deploy-webhook -n 20 --no-pager')
        journal_output = stdout.read().decode('utf-8')
        logs.append(journal_output[:1000])
        
        # Читаем скрипт деплоя
        script_path = os.path.join(os.path.dirname(__file__), 'deploy_script.py')
        with open(script_path, 'r') as f:
            deploy_script = f.read()
        
        # Команды для установки и запуска
        commands = [
            # Создаем файл скрипта
            f"cat > /tmp/deploy_server.py << 'EOFSCRIPT'\n{deploy_script}\nEOFSCRIPT",
            "sudo mv /tmp/deploy_server.py /usr/local/bin/deploy_server.py",
            "sudo chmod +x /usr/local/bin/deploy_server.py",
            
            # Создаем systemd сервис
            """sudo tee /etc/systemd/system/deploy-webhook.service > /dev/null << 'EOFSERVICE'
[Unit]
Description=Deploy Webhook Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/usr/local/bin
ExecStart=/usr/bin/python3 /usr/local/bin/deploy_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOFSERVICE""",
            
            # Запускаем сервис
            "sudo systemctl daemon-reload",
            "sudo systemctl enable deploy-webhook",
            "sudo systemctl stop deploy-webhook",
            "sudo systemctl start deploy-webhook",
            "sleep 2",
            "sudo systemctl status deploy-webhook --no-pager"
        ]
        
        logs.append("⚙️ Устанавливаю и запускаю webhook сервис...")
        
        # Выполняем команды
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            exit_code = stdout.channel.recv_exit_status()
            
            if exit_code != 0 and 'systemctl status' not in cmd:
                error = stderr.read().decode()
                logs.append(f"⚠️ Ошибка команды: {cmd[:50]}...")
                logs.append(f"   {error}")
            
            # Для status команды показываем вывод
            if 'systemctl status' in cmd:
                status_output = stdout.read().decode()
                if 'Active: active (running)' in status_output:
                    logs.append("✅ Webhook сервис запущен и работает!")
                else:
                    logs.append("⚠️ Статус сервиса:")
                    logs.append(status_output[:500])
        
        ssh.close()
        logs.append("✅ SSH соединение закрыто")
        logs.append("🎉 Проверяй webhook: http://158.160.115.239:9000/deploy")
        
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