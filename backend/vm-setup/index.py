import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import base64


def handler(event, context):
    """Автоматическое создание и настройка VM с генерацией SSH ключей"""
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
        import time
        import re
        
        body = json.loads(event.get('body', '{}'))
        vm_name = body.get('name', '').strip()
        
        print(f"DEBUG: Received vm_name from user: '{vm_name}'")
        
        if not vm_name:
            vm_name = f'vm{int(time.time())}'
            print(f"DEBUG: Empty name, using: '{vm_name}'")
        
        print(f"DEBUG: Will create VM with name: '{vm_name}'")
        
        dsn = os.environ['DATABASE_URL']
        schema = os.environ.get('MAIN_DB_SCHEMA', 'public')
        conn = psycopg2.connect(dsn)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Проверяем существует ли VM с таким именем
        cur.execute(
            f"SELECT id, name, status FROM {schema}.vm_instances WHERE name = %s",
            (vm_name,)
        )
        existing = cur.fetchone()
        if existing:
            cur.close()
            conn.close()
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': f'VM с именем "{vm_name}" уже существует. Используй другое имя.'}),
                'isBase64Encoded': False
            }
        
        # Генерируем SSH ключи
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()
        
        public_key = private_key.public_key()
        public_ssh = public_key.public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH
        ).decode()
        
        # Получаем IAM токен
        oauth_token = os.environ['YANDEX_CLOUD_TOKEN']
        iam_response = requests.post(
            'https://iam.api.cloud.yandex.net/iam/v1/tokens',
            json={'yandexPassportOauthToken': oauth_token},
            timeout=10
        )
        
        if iam_response.status_code != 200:
            raise Exception(f'IAM token error: {iam_response.text}')
        
        iam_token = iam_response.json()['iamToken']
        
        # Получаем folder_id
        folder_id = get_folder_id(iam_token)
        
        # Получаем subnet_id
        subnet_id = get_subnet_id(iam_token, folder_id)
        
        # Cloud-init скрипт для автонастройки
        cloud_init = f"""#cloud-config
users:
  - name: ubuntu
    groups: sudo
    shell: /bin/bash
    sudo: ['ALL=(ALL) NOPASSWD:ALL']
    ssh-authorized-keys:
      - {public_ssh}

package_update: true
package_upgrade: true

packages:
  - nginx
  - git
  - curl
  - postgresql
  - postgresql-contrib
  - nodejs
  - npm

runcmd:
  - curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  - apt-get install -y nodejs
  - npm install -g npm@latest
  - systemctl start nginx
  - systemctl enable nginx
  - systemctl start postgresql
  - systemctl enable postgresql
  - mkdir -p /var/www
  - chown -R ubuntu:ubuntu /var/www
"""
        
        # Создаём VM (используем минимальную конфигурацию)
        vm_payload = {
            "folderId": folder_id,
            "name": vm_name,
            "zoneId": "ru-central1-a",
            "platformId": "standard-v3",
            "resourcesSpec": {
                "memory": "2147483648",
                "cores": "2",
                "coreFraction": "20"
            },
            "metadata": {
                "user-data": cloud_init,
                "serial-port-enable": "1"
            },
            "bootDiskSpec": {
                "mode": "READ_WRITE",
                "autoDelete": True,
                "diskSpec": {
                    "size": "21474836480",
                    "typeId": "network-hdd",
                    "imageId": "fd8kdq6d0p8sij7h5qe3"
                }
            },
            "networkInterfaceSpecs": [{
                "subnetId": subnet_id,
                "primaryV4AddressSpec": {
                    "oneToOneNatSpec": {
                        "ipVersion": "IPV4"
                    }
                }
            }],
            "schedulingPolicy": {
                "preemptible": False
            }
        }
        
        response = requests.post(
            'https://compute.api.cloud.yandex.net/compute/v1/instances',
            headers={
                'Authorization': f'Bearer {iam_token}',
                'Content-Type': 'application/json'
            },
            json=vm_payload,
            timeout=30
        )
        
        if response.status_code not in [200, 201]:
            raise Exception(f'VM creation failed: {response.text}')
        
        result = response.json()
        yandex_vm_id = result['metadata']['instanceId']
        
        # Ждём получения IP адреса
        import time
        ip_address = None
        for _ in range(30):
            vm_info = requests.get(
                f'https://compute.api.cloud.yandex.net/compute/v1/instances/{yandex_vm_id}',
                headers={'Authorization': f'Bearer {iam_token}'},
                timeout=10
            )
            
            if vm_info.status_code == 200:
                vm_data = vm_info.json()
                interfaces = vm_data.get('networkInterfaces', [])
                if interfaces:
                    nat_address = interfaces[0].get('primaryV4Address', {}).get('oneToOneNat', {})
                    if nat_address.get('address'):
                        ip_address = nat_address['address']
                        break
            
            time.sleep(2)
        
        if not ip_address:
            raise Exception('Failed to get VM IP address')
        
        # Сохраняем в БД со статусом initializing
        cur.execute(
            f"""
            INSERT INTO {schema}.vm_instances 
            (name, ip_address, ssh_user, ssh_private_key, yandex_vm_id, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (vm_name, ip_address, 'ubuntu', private_pem, yandex_vm_id, 'initializing')
        )
        
        vm_id = cur.fetchone()['id']
        conn.commit()
        
        print(f"DEBUG: VM created, waiting for SSH to be ready...")
        
        # Ждём пока SSH станет доступен (cloud-init завершится)
        ssh_ready = False
        for attempt in range(60):  # 60 попыток по 5 секунд = 5 минут
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                from io import StringIO
                pkey = paramiko.RSAKey.from_private_key(StringIO(private_pem))
                ssh.connect(
                    hostname=ip_address,
                    username='ubuntu',
                    pkey=pkey,
                    timeout=5,
                    allow_agent=False,
                    look_for_keys=False
                )
                ssh.close()
                ssh_ready = True
                print(f"DEBUG: SSH is ready after {attempt + 1} attempts")
                break
            except Exception as e:
                print(f"DEBUG: SSH attempt {attempt + 1}/60 failed: {str(e)}")
                time.sleep(5)
        
        # Обновляем статус
        final_status = 'running' if ssh_ready else 'ssh_pending'
        cur.execute(
            f"UPDATE {schema}.vm_instances SET status = %s WHERE id = %s",
            (final_status, vm_id)
        )
        conn.commit()
        
        cur.close()
        conn.close()
        
        message = f'Сервер создан! IP: {ip_address}'
        if not ssh_ready:
            message += ' (SSH инициализируется, подожди 2-3 минуты перед деплоем)'
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'vm_id': vm_id,
                'name': vm_name,
                'ip_address': ip_address,
                'yandex_vm_id': yandex_vm_id,
                'ssh_ready': ssh_ready,
                'message': message
            }),
            'isBase64Encoded': False
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)}),
            'isBase64Encoded': False
        }


def get_folder_id(iam_token):
    """Получить folder_id из Yandex Cloud"""
    headers = {'Authorization': f'Bearer {iam_token}'}
    
    clouds_resp = requests.get(
        'https://resource-manager.api.cloud.yandex.net/resource-manager/v1/clouds',
        headers=headers,
        timeout=10
    )
    
    if clouds_resp.status_code != 200:
        raise Exception(f'Failed to get clouds: {clouds_resp.text}')
    
    clouds = clouds_resp.json().get('clouds', [])
    if not clouds:
        raise Exception('No clouds found')
    
    cloud_id = clouds[0]['id']
    
    folders_resp = requests.get(
        f'https://resource-manager.api.cloud.yandex.net/resource-manager/v1/folders?cloudId={cloud_id}',
        headers=headers,
        timeout=10
    )
    
    folders = folders_resp.json().get('folders', [])
    if not folders:
        raise Exception('No folders found')
    
    return folders[0]['id']


def get_subnet_id(iam_token, folder_id):
    """Получить или создать subnet"""
    headers = {'Authorization': f'Bearer {iam_token}'}
    
    # Получаем сети
    nets_resp = requests.get(
        f'https://vpc.api.cloud.yandex.net/vpc/v1/networks?folderId={folder_id}',
        headers=headers,
        timeout=10
    )
    
    networks = nets_resp.json().get('networks', [])
    
    if not networks:
        # Создаём сеть
        create_net = requests.post(
            'https://vpc.api.cloud.yandex.net/vpc/v1/networks',
            headers={**headers, 'Content-Type': 'application/json'},
            json={'folderId': folder_id, 'name': 'default-network'},
            timeout=10
        )
        
        if create_net.status_code not in [200, 201]:
            raise Exception(f'Failed to create network: {create_net.text}')
        
        network_id = create_net.json()['id']
    else:
        network_id = networks[0]['id']
    
    # Получаем подсети
    subnets_resp = requests.get(
        f'https://vpc.api.cloud.yandex.net/vpc/v1/subnets?folderId={folder_id}',
        headers=headers,
        timeout=10
    )
    
    subnets = subnets_resp.json().get('subnets', [])
    
    for subnet in subnets:
        if subnet.get('zoneId') == 'ru-central1-a':
            return subnet['id']
    
    # Создаём подсеть
    create_subnet = requests.post(
        'https://vpc.api.cloud.yandex.net/vpc/v1/subnets',
        headers={**headers, 'Content-Type': 'application/json'},
        json={
            'folderId': folder_id,
            'name': 'subnet-a',
            'networkId': network_id,
            'zoneId': 'ru-central1-a',
            'v4CidrBlocks': ['10.128.0.0/24']
        },
        timeout=10
    )
    
    if create_subnet.status_code not in [200, 201]:
        raise Exception(f'Failed to create subnet: {create_subnet.text}')
    
    return create_subnet.json()['id']