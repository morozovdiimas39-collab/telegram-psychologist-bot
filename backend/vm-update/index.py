import json
import os
import requests
import base64


def handler(event: dict, context) -> dict:
    """Обновить скрипт деплоя на VM через Yandex Cloud API"""
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
        
        logs = []
        logs.append("🔐 Получаю IAM токен...")
        
        # Получаем IAM токен
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
        
        # Получаем cloud и folder ID
        logs.append("☁️ Получаю cloud ID...")
        clouds_resp = requests.get(
            "https://resource-manager.api.cloud.yandex.net/resource-manager/v1/clouds",
            headers=headers,
            timeout=10
        )
        
        clouds = clouds_resp.json().get("clouds", [])
        if not clouds:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'No clouds found', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        cloud_id = clouds[0]["id"]
        
        logs.append("📁 Получаю folder ID...")
        folders_resp = requests.get(
            f"https://resource-manager.api.cloud.yandex.net/resource-manager/v1/folders?cloudId={cloud_id}",
            headers=headers,
            timeout=10
        )
        
        folders = folders_resp.json().get("folders", [])
        if not folders:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'No folders found', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        folder_id = folders[0]["id"]
        
        # Находим VM
        logs.append("🔍 Ищу VM deploy-server...")
        instances_resp = requests.get(
            f"https://compute.api.cloud.yandex.net/compute/v1/instances?folderId={folder_id}",
            headers=headers,
            timeout=10
        )
        
        instances = instances_resp.json().get("instances", [])
        vm_id = None
        for vm in instances:
            if vm.get("name") == "deploy-server":
                vm_id = vm["id"]
                break
        
        if not vm_id:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'VM deploy-server not found', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        logs.append(f"✅ VM найдена: {vm_id}")
        
        # Читаем скрипт деплоя
        script_path = os.path.join(os.path.dirname(__file__), 'deploy_script.py')
        with open(script_path, 'r') as f:
            deploy_script = f.read()
        
        # Обновляем метаданные VM с новым user-data
        logs.append("📦 Обновляю метаданные VM...")
        
        user_data = f"""#cloud-config
write_files:
  - path: /usr/local/bin/deploy_server.py
    permissions: '0755'
    content: |
{chr(10).join('      ' + line for line in deploy_script.split(chr(10)))}

runcmd:
  - pkill -f deploy_server.py || true
  - nohup python3 /usr/local/bin/deploy_server.py > /var/log/deploy_server.log 2>&1 &
"""
        
        update_payload = {
            "updateMask": "metadata",
            "metadata": {
                "user-data": user_data
            }
        }
        
        update_resp = requests.patch(
            f"https://compute.api.cloud.yandex.net/compute/v1/instances/{vm_id}",
            headers={**headers, "Content-Type": "application/json"},
            json=update_payload,
            timeout=30
        )
        
        if update_resp.status_code not in [200, 202]:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'Update failed: {update_resp.text}', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        logs.append("✅ Метаданные обновлены")
        logs.append("🔄 Перезагружаю VM для применения изменений...")
        
        # Перезагружаем VM
        restart_resp = requests.post(
            f"https://compute.api.cloud.yandex.net/compute/v1/instances/{vm_id}:restart",
            headers=headers,
            timeout=10
        )
        
        if restart_resp.status_code == 200:
            logs.append("✅ VM перезагружается (займёт 1-2 минуты)")
        else:
            logs.append("⚠️ Не удалось перезагрузить автоматически, перезагрузи вручную через консоль YC")
        
        logs.append("🎉 Скрипт деплоя обновлён! После перезагрузки VM будет готова")
        
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
