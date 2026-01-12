import json
import os
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


def handler(event: dict, context) -> dict:
    """Создать VM с SSH ключом"""
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
        oauth_token = os.environ.get('YANDEX_CLOUD_TOKEN')
        
        logs = []
        logs.append("🔐 Получаю IAM токен...")
        
        iam_resp = requests.post(
            "https://iam.api.cloud.yandex.net/iam/v1/tokens",
            json={"yandexPassportOauthToken": oauth_token},
            timeout=10
        )
        
        if iam_resp.status_code != 200:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'IAM error: {iam_resp.text}', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        iam_token = iam_resp.json()["iamToken"]
        logs.append("✅ IAM токен получен")
        
        headers = {"Authorization": f"Bearer {iam_token}"}
        
        logs.append("☁️ Получаю cloud и folder ID...")
        clouds_resp = requests.get(
            "https://resource-manager.api.cloud.yandex.net/resource-manager/v1/clouds",
            headers=headers,
            timeout=10
        )
        
        clouds = clouds_resp.json().get("clouds", [])
        cloud_id = clouds[0]["id"]
        
        folders_resp = requests.get(
            f"https://resource-manager.api.cloud.yandex.net/resource-manager/v1/folders?cloudId={cloud_id}",
            headers=headers,
            timeout=10
        )
        
        folders = folders_resp.json().get("folders", [])
        folder_id = folders[0]["id"]
        
        # Генерируем SSH ключ
        logs.append("🔑 Генерирую SSH ключ...")
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        public_key = private_key.public_key()
        public_ssh = public_key.public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH
        ).decode('utf-8')
        
        logs.append("✅ SSH ключ сгенерирован")
        
        # Читаем скрипт деплоя
        script_path = os.path.join(os.path.dirname(__file__), 'deploy_script.py')
        with open(script_path, 'r') as f:
            deploy_script = f.read()
        
        # Cloud-init с SSH ключом
        cloud_init = f"""#cloud-config
package_update: true
packages:
  - docker.io
  - nginx
  - postgresql
  - postgresql-contrib
  - python3-pip
  - python3-flask
  - git
  - nodejs
  - npm

users:
  - name: ubuntu
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys:
      - {public_ssh}

write_files:
  - path: /usr/local/bin/deploy_server.py
    permissions: '0755'
    content: |
{chr(10).join('      ' + line for line in deploy_script.split(chr(10)))}

  - path: /etc/systemd/system/deploy-webhook.service
    permissions: '0644'
    content: |
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

runcmd:
  - systemctl enable docker && systemctl start docker
  - systemctl enable nginx && systemctl start nginx
  - systemctl enable postgresql && systemctl start postgresql
  - sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
  - sudo -u postgres psql -c "ALTER USER postgres WITH SUPERUSER;"
  - echo "host all all 0.0.0.0/0 md5" >> /etc/postgresql/*/main/pg_hba.conf
  - echo "listen_addresses = '*'" >> /etc/postgresql/*/main/postgresql.conf
  - systemctl restart postgresql
  - mkdir -p /var/www
  - chown -R www-data:www-data /var/www
  - pip3 install flask requests
  - systemctl daemon-reload
  - systemctl enable deploy-webhook
  - systemctl start deploy-webhook
  - sleep 5
  - systemctl status deploy-webhook > /var/log/webhook-status.log
"""
        
        # Получаем subnet
        zone = "ru-central1-a"
        logs.append(f"📡 Получаю subnet в зоне {zone}...")
        subnets_resp = requests.get(
            f"https://vpc.api.cloud.yandex.net/vpc/v1/subnets?folderId={folder_id}",
            headers=headers,
            timeout=10
        )
        subnets = subnets_resp.json().get("subnets", [])
        
        subnet_id = None
        for subnet in subnets:
            if subnet.get("zoneId") == zone:
                subnet_id = subnet["id"]
                break
        
        if not subnet_id:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'No subnet in zone {zone}', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        logs.append(f"✅ Subnet: {subnet_id}")
        
        # Создаем VM
        logs.append("🚀 Создаю VM...")
        
        vm_payload = {
            "folderId": folder_id,
            "name": "deploy-server",
            "zoneId": zone,
            "platformId": "standard-v3",
            "resourcesSpec": {"memory": "4294967296", "cores": "2"},
            "bootDiskSpec": {
                "mode": "READ_WRITE",
                "autoDelete": True,
                "diskSpec": {
                    "size": "32212254720",
                    "typeId": "network-ssd",
                    "imageId": "fd8kdq6d0p8sij7h5qe3"
                }
            },
            "networkInterfaceSpecs": [{
                "subnetId": subnet_id,
                "primaryV4AddressSpec": {"oneToOneNatSpec": {"ipVersion": "IPV4"}}
            }],
            "metadata": {"user-data": cloud_init}
        }
        
        create_resp = requests.post(
            "https://compute.api.cloud.yandex.net/compute/v1/instances",
            headers={**headers, "Content-Type": "application/json"},
            json=vm_payload,
            timeout=30
        )
        
        if create_resp.status_code != 200:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'Create failed: {create_resp.text[:300]}', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        operation_id = create_resp.json()["id"]
        logs.append(f"✅ VM создаётся: {operation_id}")
        logs.append("")
        logs.append("🎉 VM запущена с SSH ключом!")
        logs.append("")
        logs.append("VM_SSH_KEY:")
        logs.append(private_pem)
        logs.append("")
        logs.append("⏳ Через 2-3 минуты проверь webhook")
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'success': True,
                'ssh_private_key': private_pem,
                'logs': logs
            }),
            'isBase64Encoded': False
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e), 'logs': logs if 'logs' in locals() else []}),
            'isBase64Encoded': False
        }