import json
import os
import psycopg2
import requests


def handler(event: dict, context) -> dict:
    """Создание новой VM в Yandex Cloud с автонастройкой"""
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
        vm_name = body.get('name', 'vm-1')
        
        # Подключаемся к БД
        dsn = os.environ['DATABASE_URL']
        schema = os.environ.get('MAIN_DB_SCHEMA', 'public')
        conn = psycopg2.connect(dsn)
        cur = conn.cursor()
        
        # Проверяем дубликат
        cur.execute(f"SELECT id FROM {schema}.vm_instances WHERE name = %s", (vm_name,))
        if cur.fetchone():
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'VM {vm_name} уже существует'}),
                'isBase64Encoded': False
            }
        
        # Создаём запись
        cur.execute(
            f"INSERT INTO {schema}.vm_instances (name, status) VALUES (%s, 'creating') RETURNING id",
            (vm_name,)
        )
        vm_id = cur.fetchone()[0]
        conn.commit()
        
        # Получаем IAM токен
        oauth_token = os.environ['YANDEX_CLOUD_TOKEN']
        iam_response = requests.post(
            'https://iam.api.cloud.yandex.net/iam/v1/tokens',
            json={'yandexPassportOauthToken': oauth_token},
            timeout=10
        )
        iam_token = iam_response.json()['iamToken']
        
        # Получаем folder_id
        folder_id = get_folder_id(iam_token)
        
        # Получаем subnet_id
        subnet_id = get_subnet_id(iam_token, folder_id)
        
        # Создаём VM
        ssh_key = os.environ.get('VM_SSH_PUBLIC_KEY', 'ssh-rsa AAAAB3...')
        
        vm_payload = {
            "folderId": folder_id,
            "name": vm_name,
            "zoneId": "ru-central1-a",
            "platformId": "standard-v2",
            "resourcesSpec": {"memory": str(2*1024*1024*1024), "cores": 2},
            "metadata": {"user-data": cloud_init_script(ssh_key)},
            "bootDiskSpec": {
                "mode": "READ_WRITE",
                "autoDelete": True,
                "diskSpec": {"size": str(20*1024*1024*1024), "imageId": "fd8kdq6d0p8sij7h5qe3"}
            },
            "networkInterfaceSpecs": [{
                "subnetId": subnet_id,
                "primaryV4AddressSpec": {"oneToOneNatSpec": {"ipVersion": "IPV4"}}
            }]
        }
        
        response = requests.post(
            'https://compute.api.cloud.yandex.net/compute/v1/instances',
            headers={'Authorization': f'Bearer {iam_token}', 'Content-Type': 'application/json'},
            json=vm_payload,
            timeout=30
        )
        
        if response.status_code not in [200, 201]:
            raise Exception(f'Ошибка создания VM: {response.text}')
        
        operation_id = response.json()['id']
        
        # Обновляем статус
        cur.execute(
            f"UPDATE {schema}.vm_instances SET yandex_vm_id = %s, status = 'creating' WHERE id = %s",
            (operation_id, vm_id)
        )
        conn.commit()
        
        return {
            'statusCode': 202,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'success': True,
                'vm_id': vm_id,
                'name': vm_name,
                'operation_id': operation_id,
                'status': 'creating',
                'message': 'VM создаётся, подождите 2-3 минуты'
            }),
            'isBase64Encoded': False
        }
        
    except Exception as e:
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


def get_folder_id(iam_token: str) -> str:
    """Получить folder_id"""
    headers = {'Authorization': f'Bearer {iam_token}'}
    clouds_resp = requests.get(
        'https://resource-manager.api.cloud.yandex.net/resource-manager/v1/clouds',
        headers=headers,
        timeout=10
    )
    cloud_id = clouds_resp.json()['clouds'][0]['id']
    
    folders_resp = requests.get(
        f'https://resource-manager.api.cloud.yandex.net/resource-manager/v1/folders?cloudId={cloud_id}',
        headers=headers,
        timeout=10
    )
    return folders_resp.json()['folders'][0]['id']


def get_subnet_id(iam_token: str, folder_id: str) -> str:
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
            json={'folderId': folder_id, 'name': 'default-net'},
            timeout=10
        )
        network_id = create_net.json()['response']['id']
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
    return create_subnet.json()['response']['id']


def cloud_init_script(ssh_key: str) -> str:
    """Cloud-init для автонастройки"""
    return f"""#cloud-config
users:
  - name: ubuntu
    groups: sudo
    shell: /bin/bash
    sudo: ['ALL=(ALL) NOPASSWD:ALL']
    ssh-authorized-keys:
      - {ssh_key}

package_update: true
packages: [nginx, git, curl, python3-pip, python3-flask]

write_files:
  - path: /opt/webhook/app.py
    content: |
      from flask import Flask, request, jsonify
      import subprocess, os
      app = Flask(__name__)
      
      @app.route('/deploy', methods=['POST'])
      def deploy():
          data = request.json
          project_dir = '/var/www/app'
          os.makedirs(project_dir, exist_ok=True)
          
          repo_url = data.get('repo_url')
          if repo_url:
              if os.path.exists(f'{{project_dir}}/.git'):
                  subprocess.run(['git', '-C', project_dir, 'pull'], check=True)
              else:
                  subprocess.run(['git', 'clone', repo_url, project_dir], check=True)
          
          subprocess.run(['/root/.bun/bin/bun', 'install'], cwd=project_dir, check=True)
          subprocess.run(['/root/.bun/bin/bun', 'run', 'build'], cwd=project_dir, check=True)
          return jsonify({{'success': True}})
      
      app.run(host='0.0.0.0', port=9000)

runcmd:
  - curl -fsSL https://bun.sh/install | bash
  - mkdir -p /var/www /opt/webhook
  - python3 /opt/webhook/app.py &
  - echo 'server {{ listen 80; root /var/www/app/dist; location / {{ try_files $uri /index.html; }} }}' > /etc/nginx/sites-available/default
  - systemctl restart nginx
"""
