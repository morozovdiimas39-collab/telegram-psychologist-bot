import json
import os
import requests


def handler(event: dict, context) -> dict:
    """Создать VM в Yandex Cloud автоматически"""
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

    oauth_token = os.environ.get('YANDEX_CLOUD_TOKEN')
    
    try:
        logs = ["🔐 Получаю IAM токен..."]
        
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
        
        logs.append("☁️ Получаю cloud ID...")
        clouds_resp = requests.get(
            "https://resource-manager.api.cloud.yandex.net/resource-manager/v1/clouds",
            headers=headers,
            timeout=10
        )
        
        if clouds_resp.status_code != 200:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'Clouds API error: {clouds_resp.text}', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        clouds = clouds_resp.json().get("clouds", [])
        if not clouds:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'No clouds found in account', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        cloud_id = clouds[0]["id"]
        logs.append(f"✅ Cloud ID: {cloud_id}")
        
        logs.append("📁 Получаю folder ID...")
        folders_resp = requests.get(
            f"https://resource-manager.api.cloud.yandex.net/resource-manager/v1/folders?cloudId={cloud_id}",
            headers=headers,
            timeout=10
        )
        
        if folders_resp.status_code != 200:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'Folders API error: {folders_resp.text}', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        folders = folders_resp.json().get("folders", [])
        if not folders:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'No folders found in cloud', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        folder_id = folders[0]["id"]
        logs.append(f"✅ Folder ID: {folder_id}")
        
        logs.append("🔍 Проверяю VM...")
        instances_resp = requests.get(
            f"https://compute.api.cloud.yandex.net/compute/v1/instances?folderId={folder_id}",
            headers=headers,
            timeout=10
        )
        instances = instances_resp.json().get("instances", [])
        
        for vm in instances:
            if vm.get("name") == "deploy-server":
                logs.append("✅ VM уже существует!")
                vm_ip = None
                for iface in vm.get("networkInterfaces", []):
                    nat = iface.get("primaryV4Address", {}).get("oneToOneNat", {})
                    vm_ip = nat.get("address")
                    if vm_ip:
                        break
                
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({
                        'success': True,
                        'ip': vm_ip,
                        'webhook': f"http://{vm_ip}:9000/deploy",
                        'logs': logs
                    }),
                    'isBase64Encoded': False
                }
        
        logs.append("⚠️ VM не найдена, создаю...")
        
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
                'body': json.dumps({'error': f'No subnet found in zone {zone}', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        logs.append(f"✅ Subnet: {subnet_id}")
        
        cloud_init = """#cloud-config
package_update: true
packages:
  - docker.io
  - nginx
  - postgresql
  - python3-pip
  - git
runcmd:
  - systemctl enable docker && systemctl start docker
  - systemctl enable nginx && systemctl start nginx
  - sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
"""
        
        logs.append("🚀 Создаю VM...")
        
        vm_payload = {
            "folderId": folder_id,
            "name": "deploy-server",
            "zoneId": "ru-central1-a",
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
        logs.append(f"✅ Операция запущена: {operation_id}")
        logs.append("⏳ VM создаётся 2-3 минуты, повтори запрос через минуту")
        
        return {
            'statusCode': 202,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'success': True, 'operation_id': operation_id, 'logs': logs}),
            'isBase64Encoded': False
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)}),
            'isBase64Encoded': False
        }