import json
import os
import time
import psycopg2
import requests
from psycopg2.extras import RealDictCursor


def handler(event: dict, context) -> dict:
    """Создание VM в Yandex Cloud с установкой nginx, bun, certbot
    
    Если указан existing_vm=true, то использует существующую VM из секретов
    """
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
        if not body_str or body_str == '':
            body_str = '{}'
        body = json.loads(body_str) if isinstance(body_str, str) else body_str
        vm_name = body.get('name', 'deploy-vm-1')
        use_existing = body.get('existing_vm', False)
        
        # Подключаемся к БД
        dsn = os.environ['DATABASE_URL']
        schema = os.environ.get('MAIN_DB_SCHEMA', 'public')
        conn = psycopg2.connect(dsn)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Если используем существующую VM из секретов
        if use_existing:
            existing_ip = os.environ.get('VM_IP_ADDRESS')
            existing_ssh_key = os.environ.get('VM_SSH_PUBLIC_KEY', 'ssh-rsa AAAAB3NzaC1...')
            
            if not existing_ip:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'VM_IP_ADDRESS не найден в секретах'}),
                    'isBase64Encoded': False
                }
            
            # Проверяем, нет ли уже такой VM
            cur.execute(
                f"SELECT id FROM {schema}.vm_instances WHERE ip_address = %s",
                (existing_ip,)
            )
            if cur.fetchone():
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': f'VM с IP {existing_ip} уже добавлена'}),
                    'isBase64Encoded': False
                }
            
            # Добавляем существующую VM в БД
            cur.execute(
                f"""
                INSERT INTO {schema}.vm_instances (name, ip_address, ssh_key, status)
                VALUES (%s, %s, %s, 'ready')
                RETURNING id
                """,
                (vm_name, existing_ip, existing_ssh_key)
            )
            vm_record = cur.fetchone()
            conn.commit()
            
            return {
                'statusCode': 201,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'success': True,
                    'vm_id': vm_record['id'],
                    'name': vm_name,
                    'ip_address': existing_ip,
                    'status': 'ready',
                    'message': 'Существующая VM добавлена в систему'
                }),
                'isBase64Encoded': False
            }
        
        # Проверяем, нет ли уже VM с таким именем
        cur.execute(
            f"SELECT id, status FROM {schema}.vm_instances WHERE name = %s",
            (vm_name,)
        )
        existing = cur.fetchone()
        
        if existing:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'VM с именем {vm_name} уже существует'}),
                'isBase64Encoded': False
            }
        
        # Создаём запись в БД
        cur.execute(
            f"""
            INSERT INTO {schema}.vm_instances (name, status)
            VALUES (%s, 'creating')
            RETURNING id
            """,
            (vm_name,)
        )
        vm_record = cur.fetchone()
        vm_id = vm_record['id']
        conn.commit()
        
        # Получаем IAM токен через OAuth
        iam_token = get_iam_token()
        folder_id = os.environ.get('YANDEX_FOLDER_ID', 'b1g8dn6bs6vq7v3jqfta')
        
        # Генерируем SSH ключ (публичный)
        ssh_pub_key = generate_ssh_key_pair()
        
        # Создаём VM через Yandex Cloud API
        create_vm_payload = {
            "folderId": folder_id,
            "name": vm_name,
            "zoneId": "ru-central1-a",
            "platformId": "standard-v2",
            "resourcesSpec": {
                "memory": str(2 * 1024 * 1024 * 1024),  # 2GB
                "cores": 2
            },
            "metadata": {
                "user-data": get_cloud_init_script(ssh_pub_key)
            },
            "bootDiskSpec": {
                "mode": "READ_WRITE",
                "autoDelete": True,
                "diskSpec": {
                    "size": str(20 * 1024 * 1024 * 1024),  # 20GB
                    "imageId": "fd8kdq6d0p8sij7h5qe3"  # Ubuntu 22.04
                }
            },
            "networkInterfaceSpecs": [{
                "subnetId": os.environ.get('YANDEX_SUBNET_ID', 'e9b95m6ai9kv8r1tjf4l'),
                "primaryV4AddressSpec": {
                    "oneToOneNatSpec": {
                        "ipVersion": "IPV4"
                    }
                }
            }]
        }
        
        headers = {
            'Authorization': f'Bearer {iam_token}',
            'Content-Type': 'application/json'
        }
        
        # Создаём VM
        response = requests.post(
            'https://compute.api.cloud.yandex.net/compute/v1/instances',
            headers=headers,
            json=create_vm_payload,
            timeout=30
        )
        
        if response.status_code not in [200, 201]:
            raise Exception(f'Ошибка создания VM: {response.text}')
        
        operation = response.json()
        operation_id = operation['id']
        
        # Ждём завершения операции (асинхронно, не блокируем)
        # В реальности нужно делать polling, но для Cloud Function делаем упрощённо
        time.sleep(5)
        
        # Проверяем статус операции
        op_response = requests.get(
            f'https://operation.api.cloud.yandex.net/operations/{operation_id}',
            headers=headers,
            timeout=10
        )
        
        op_data = op_response.json()
        
        if not op_data.get('done'):
            # Операция ещё выполняется
            cur.execute(
                f"""
                UPDATE {schema}.vm_instances 
                SET status = 'creating', yandex_vm_id = %s
                WHERE id = %s
                """,
                (operation_id, vm_id)
            )
            conn.commit()
            
            return {
                'statusCode': 202,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'message': 'VM создаётся, это займёт 1-2 минуты',
                    'vm_id': vm_id,
                    'operation_id': operation_id,
                    'status': 'creating'
                }),
                'isBase64Encoded': False
            }
        
        # VM создана
        if 'error' in op_data:
            raise Exception(f"Ошибка создания VM: {op_data['error']}")
        
        # Получаем ID созданной VM
        yandex_vm_id = op_data['response']['id']
        
        # Получаем информацию о VM (IP адрес)
        vm_info_response = requests.get(
            f'https://compute.api.cloud.yandex.net/compute/v1/instances/{yandex_vm_id}',
            headers=headers,
            timeout=10
        )
        
        vm_info = vm_info_response.json()
        ip_address = vm_info['networkInterfaces'][0]['primaryV4Address']['oneToOneNat']['address']
        
        # Обновляем запись в БД
        cur.execute(
            f"""
            UPDATE {schema}.vm_instances 
            SET ip_address = %s, 
                ssh_key = %s, 
                yandex_vm_id = %s,
                status = 'ready',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (ip_address, ssh_pub_key, yandex_vm_id, vm_id)
        )
        conn.commit()
        
        return {
            'statusCode': 201,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'success': True,
                'vm_id': vm_id,
                'name': vm_name,
                'ip_address': ip_address,
                'status': 'ready',
                'message': 'VM успешно создана и настроена'
            }),
            'isBase64Encoded': False
        }
        
    except KeyError as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': f'Секрет не найден: {str(e)}'}),
            'isBase64Encoded': False
        }
    except Exception as e:
        # Обновляем статус на error
        if 'vm_id' in locals():
            try:
                cur.execute(
                    f"UPDATE {schema}.vm_instances SET status = 'error' WHERE id = %s",
                    (vm_id,)
                )
                conn.commit()
            except:
                pass
        
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)}),
            'isBase64Encoded': False
        }
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()


def generate_ssh_key_pair():
    """Генерирует SSH ключ (в реальности используем существующий из секретов)"""
    # В production нужно генерировать новую пару, но для простоты используем готовый
    return os.environ.get('VM_SSH_PUBLIC_KEY', 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC...')


def get_iam_token() -> str:
    """Получить IAM токен через OAuth токен Yandex Cloud"""
    oauth_token = os.environ.get('YANDEX_CLOUD_TOKEN')
    if not oauth_token:
        raise Exception('YANDEX_CLOUD_TOKEN не найден в секретах')
    
    response = requests.post(
        'https://iam.api.cloud.yandex.net/iam/v1/tokens',
        json={'yandexPassportOauthToken': oauth_token},
        timeout=10
    )
    
    if response.status_code != 200:
        raise Exception(f'Ошибка получения IAM токена: {response.text}')
    
    return response.json()['iamToken']


def get_cloud_init_script(ssh_pub_key: str) -> str:
    """Cloud-init скрипт для настройки VM при первом запуске"""
    return f"""#cloud-config
users:
  - name: ubuntu
    groups: sudo
    shell: /bin/bash
    sudo: ['ALL=(ALL) NOPASSWD:ALL']
    ssh-authorized-keys:
      - {ssh_pub_key}

package_update: true
package_upgrade: true

packages:
  - nginx
  - certbot
  - python3-certbot-nginx
  - git
  - curl
  - unzip

runcmd:
  - curl -fsSL https://bun.sh/install | bash
  - ln -s /root/.bun/bin/bun /usr/local/bin/bun
  - systemctl enable nginx
  - systemctl start nginx
  - mkdir -p /var/www
  - chown -R ubuntu:ubuntu /var/www
  - echo "VM готова к деплою" > /var/www/ready.txt
"""