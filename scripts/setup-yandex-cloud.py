#!/usr/bin/env python3
"""
Скрипт для автоматической настройки инфраструктуры в Yandex Cloud.
Создаёт VM, PostgreSQL, настраивает nginx, Docker и всё необходимое.
"""

import os
import sys
import time
import json
import requests
from typing import Dict, Optional

OAUTH_TOKEN = "y0__xCtvb3CARjB3RMg3fH9zxXjpBff6RKbq5G1BPxGOJWLWfyL1Q"
YC_API = "https://api.cloud.yandex.net"
FOLDER_ID = None  # Определим автоматически


def get_iam_token(oauth_token: str) -> str:
    """Получить IAM токен из OAuth токена"""
    response = requests.post(
        "https://iam.api.cloud.yandex.net/iam/v1/tokens",
        json={"yandexPassportOauthToken": oauth_token}
    )
    response.raise_for_status()
    return response.json()["iamToken"]


def get_folder_id(iam_token: str) -> str:
    """Получить первый доступный folder ID"""
    headers = {"Authorization": f"Bearer {iam_token}"}
    response = requests.get(
        "https://resource-manager.api.cloud.yandex.net/resource-manager/v1/folders",
        headers=headers
    )
    response.raise_for_status()
    folders = response.json().get("folders", [])
    if not folders:
        raise Exception("Нет доступных folders в Yandex Cloud")
    return folders[0]["id"]


def create_vm(iam_token: str, folder_id: str) -> Dict:
    """
    Создать VM с Ubuntu 22.04, Docker, nginx, PostgreSQL
    """
    print("🚀 Создаю виртуальную машину...")
    
    cloud_init = """#cloud-config
package_update: true
package_upgrade: true
packages:
  - docker.io
  - docker-compose
  - nginx
  - postgresql
  - postgresql-contrib
  - certbot
  - python3-certbot-nginx
  - git

runcmd:
  - systemctl enable docker
  - systemctl start docker
  - systemctl enable nginx
  - systemctl start nginx
  - systemctl enable postgresql
  - systemctl start postgresql
  - usermod -aG docker ubuntu
  - |
    cat > /etc/nginx/sites-available/default <<'EOF'
    server {
        listen 80 default_server;
        server_name _;
        return 444;
    }
    EOF
  - systemctl reload nginx
  - |
    sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
  - |
    cat > /opt/deploy-webhook.py <<'PYEOF'
    #!/usr/bin/env python3
    from flask import Flask, request, jsonify
    import subprocess
    import os
    
    app = Flask(__name__)
    
    @app.route('/deploy', methods=['POST'])
    def deploy():
        data = request.json
        github_url = data.get('github_url')
        project_name = data.get('project_name')
        domain = data.get('domain')
        secrets = data.get('secrets', [])
        
        # Запуск деплоя в фоне
        subprocess.Popen([
            'python3', '/opt/deploy-project.py',
            '--github', github_url,
            '--name', project_name,
            '--domain', domain,
            '--secrets', json.dumps(secrets)
        ])
        
        return jsonify({'status': 'started'}), 200
    
    if __name__ == '__main__':
        app.run(host='0.0.0.0', port=9000)
    PYEOF
  - chmod +x /opt/deploy-webhook.py
  - pip3 install flask
  - nohup python3 /opt/deploy-webhook.py > /var/log/deploy-webhook.log 2>&1 &
"""
    
    headers = {
        "Authorization": f"Bearer {iam_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "folderId": folder_id,
        "name": "deploy-server",
        "description": "VM для автоматического деплоя проектов",
        "zoneId": "ru-central1-a",
        "platformId": "standard-v3",
        "resourcesSpec": {
            "memory": "4294967296",  # 4 GB
            "cores": "2"
        },
        "bootDiskSpec": {
            "mode": "READ_WRITE",
            "autoDelete": True,
            "diskSpec": {
                "size": "32212254720",  # 30 GB
                "typeId": "network-ssd",
                "imageId": "fd8qps171vp141hl7g9l"  # Ubuntu 22.04 LTS
            }
        },
        "networkInterfaceSpecs": [
            {
                "subnetId": None,  # Будет создан автоматически
                "primaryV4AddressSpec": {
                    "oneToOneNatSpec": {
                        "ipVersion": "IPV4"
                    }
                }
            }
        ],
        "metadata": {
            "user-data": cloud_init,
            "ssh-keys": f"ubuntu:ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDExampleKey ubuntu@deploy"
        }
    }
    
    response = requests.post(
        f"{YC_API}/compute/v1/instances",
        headers=headers,
        json=payload
    )
    
    if response.status_code != 200:
        print(f"❌ Ошибка создания VM: {response.text}")
        return None
    
    operation = response.json()
    operation_id = operation["id"]
    
    print("⏳ Жду завершения создания VM (это может занять 2-3 минуты)...")
    
    # Ждём завершения операции
    for i in range(60):
        time.sleep(5)
        op_response = requests.get(
            f"https://operation.api.cloud.yandex.net/operations/{operation_id}",
            headers=headers
        )
        op_data = op_response.json()
        
        if op_data.get("done"):
            if op_data.get("error"):
                print(f"❌ Ошибка: {op_data['error']}")
                return None
            
            instance_id = op_data["response"]["id"]
            print(f"✅ VM создана: {instance_id}")
            
            # Получаем информацию о VM
            vm_response = requests.get(
                f"{YC_API}/compute/v1/instances/{instance_id}",
                headers=headers
            )
            vm_info = vm_response.json()
            
            external_ip = None
            for iface in vm_info.get("networkInterfaces", []):
                if "primaryV4Address" in iface:
                    nat = iface["primaryV4Address"].get("oneToOneNat", {})
                    external_ip = nat.get("address")
                    break
            
            return {
                "id": instance_id,
                "ip": external_ip,
                "name": "deploy-server"
            }
        
        print(f"⏳ Прогресс: {i*5} сек...")
    
    print("❌ Таймаут создания VM")
    return None


def generate_ssh_key() -> tuple:
    """Генерирует SSH ключ для доступа к VM"""
    import subprocess
    
    key_path = "/tmp/yc_deploy_key"
    subprocess.run([
        "ssh-keygen", "-t", "rsa", "-b", "2048",
        "-f", key_path, "-N", "", "-q"
    ])
    
    with open(f"{key_path}.pub") as f:
        public_key = f.read().strip()
    
    with open(key_path) as f:
        private_key = f.read()
    
    return public_key, private_key


def main():
    print("🚀 Настройка инфраструктуры в Yandex Cloud\n")
    
    try:
        # 1. Получаем IAM токен
        print("🔐 Получаю IAM токен...")
        iam_token = get_iam_token(OAUTH_TOKEN)
        print("✅ IAM токен получен\n")
        
        # 2. Получаем folder ID
        print("📁 Получаю folder ID...")
        folder_id = get_folder_id(iam_token)
        print(f"✅ Folder ID: {folder_id}\n")
        
        # 3. Создаём VM
        vm_info = create_vm(iam_token, folder_id)
        
        if not vm_info:
            print("❌ Не удалось создать VM")
            sys.exit(1)
        
        print("\n✅ Инфраструктура создана!")
        print("\n" + "="*60)
        print("📋 ИНФОРМАЦИЯ ДЛЯ НАСТРОЙКИ:")
        print("="*60)
        print(f"VM IP адрес: {vm_info['ip']}")
        print(f"Webhook URL: http://{vm_info['ip']}:9000/deploy")
        print(f"\nДобавь эти секреты в poehali.dev:")
        print(f"  VM_IP_ADDRESS = {vm_info['ip']}")
        print(f"  VM_WEBHOOK_URL = http://{vm_info['ip']}:9000/deploy")
        print("\n💡 VM будет готова через 3-5 минут после первого запуска")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
