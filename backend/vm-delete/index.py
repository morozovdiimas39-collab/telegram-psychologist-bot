import json
import os
import requests


def handler(event: dict, context) -> dict:
    """Удалить VM deploy-server"""
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
            logs.append("ℹ️ VM не найдена")
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'success': True, 'logs': logs}),
                'isBase64Encoded': False
            }
        
        logs.append(f"🗑️ Удаляю VM: {vm_id}...")
        delete_resp = requests.delete(
            f"https://compute.api.cloud.yandex.net/compute/v1/instances/{vm_id}",
            headers=headers,
            timeout=30
        )
        
        if delete_resp.status_code in [200, 202]:
            logs.append("✅ VM удалена")
            logs.append("⏳ Жди 1 минуту, затем создавай новую VM")
        else:
            logs.append(f"⚠️ Ошибка удаления: {delete_resp.text}")
        
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
