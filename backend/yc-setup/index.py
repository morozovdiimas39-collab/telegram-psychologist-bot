import json
import os
import time
import requests


def handler(event: dict, context) -> dict:
    """
    API для создания инфраструктуры в Yandex Cloud.
    Создаёт VM с Docker, nginx, PostgreSQL для деплоя проектов.
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

    if method != 'POST':
        return {
            'statusCode': 405,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Method not allowed'}),
            'isBase64Encoded': False
        }

    try:
        oauth_token = os.environ.get('YANDEX_CLOUD_TOKEN')
        if not oauth_token:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'YANDEX_CLOUD_TOKEN not configured'}),
                'isBase64Encoded': False
            }

        logs = []
        logs.append("🔐 Получаю IAM токен...")
        
        iam_response = requests.post(
            "https://iam.api.cloud.yandex.net/iam/v1/tokens",
            json={"yandexPassportOauthToken": oauth_token},
            timeout=10
        )
        iam_response.raise_for_status()
        iam_token = iam_response.json()["iamToken"]
        logs.append("✅ IAM токен получен")

        logs.append("📁 Получаю folder ID...")
        headers = {"Authorization": f"Bearer {iam_token}"}
        folders_response = requests.get(
            "https://resource-manager.api.cloud.yandex.net/resource-manager/v1/folders",
            headers=headers,
            timeout=10
        )
        folders_response.raise_for_status()
        folders = folders_response.json().get("folders", [])
        
        if not folders:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'No folders found in Yandex Cloud', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        folder_id = folders[0]["id"]
        logs.append(f"✅ Folder ID: {folder_id}")

        logs.append("🔍 Проверяю существующие VM...")
        instances_response = requests.get(
            f"https://compute.api.cloud.yandex.net/compute/v1/instances?folderId={folder_id}",
            headers=headers,
            timeout=10
        )
        instances = instances_response.json().get("instances", [])
        
        existing_vm = None
        for vm in instances:
            if vm.get("name") == "deploy-server":
                existing_vm = vm
                break
        
        if existing_vm:
            vm_id = existing_vm["id"]
            logs.append(f"✅ VM уже существует: {vm_id}")
            
            external_ip = None
            for iface in existing_vm.get("networkInterfaces", []):
                nat = iface.get("primaryV4Address", {}).get("oneToOneNat", {})
                external_ip = nat.get("address")
                if external_ip:
                    break
            
            logs.append(f"📋 IP адрес: {external_ip}")
            logs.append(f"📋 Webhook: http://{external_ip}:9000/deploy")
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'success': True,
                    'vm_id': vm_id,
                    'ip_address': external_ip,
                    'webhook_url': f"http://{external_ip}:9000/deploy",
                    'logs': logs
                }),
                'isBase64Encoded': False
            }

        logs.append("🚀 Создаю новую VM...")
        logs.append("⏳ Это займёт 2-3 минуты...")

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
  - python3-pip
  - git

runcmd:
  - systemctl enable docker
  - systemctl start docker
  - systemctl enable nginx
  - systemctl start nginx
  - systemctl enable postgresql
  - systemctl start postgresql
  - usermod -aG docker ubuntu
  - sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
  - pip3 install flask requests
"""

        subnets_response = requests.get(
            f"https://vpc.api.cloud.yandex.net/vpc/v1/subnets?folderId={folder_id}",
            headers=headers,
            timeout=10
        )
        subnets = subnets_response.json().get("subnets", [])
        subnet_id = subnets[0]["id"] if subnets else None

        if not subnet_id:
            logs.append("⚠️ Нет подсетей, создаю сеть...")
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'No subnets available', 'logs': logs}),
                'isBase64Encoded': False
            }

        vm_payload = {
            "folderId": folder_id,
            "name": "deploy-server",
            "description": "VM для автоматического деплоя проектов",
            "zoneId": "ru-central1-a",
            "platformId": "standard-v3",
            "resourcesSpec": {
                "memory": "4294967296",
                "cores": "2"
            },
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
                "primaryV4AddressSpec": {
                    "oneToOneNatSpec": {"ipVersion": "IPV4"}
                }
            }],
            "metadata": {
                "user-data": cloud_init
            }
        }

        create_response = requests.post(
            "https://compute.api.cloud.yandex.net/compute/v1/instances",
            headers={**headers, "Content-Type": "application/json"},
            json=vm_payload,
            timeout=30
        )

        if create_response.status_code != 200:
            logs.append(f"❌ Ошибка создания: {create_response.text[:300]}")
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'VM creation failed', 'logs': logs}),
                'isBase64Encoded': False
            }

        operation = create_response.json()
        operation_id = operation["id"]
        logs.append(f"✅ Операция запущена: {operation_id}")
        logs.append("⏳ Жду завершения создания VM...")

        return {
            'statusCode': 202,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'success': True,
                'operation_id': operation_id,
                'logs': logs,
                'message': 'VM создаётся, проверь статус через 2-3 минуты повторным запросом'
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
