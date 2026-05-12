import json
import os
import requests
import time
from typing import Dict, Any

# Токен берем из переменной окружения
OAUTH_TOKEN = os.environ.get('YANDEX_CLOUD_TOKEN', "y0__xCtvb3CARjB3RMg3fH9zxXjpBff6RKbq5G1BPxGOJWLWfyL1Q")

def get_iam_token():
    resp = requests.post(
        "https://iam.api.cloud.yandex.net/iam/v1/tokens",
        json={"yandexPassportOauthToken": OAUTH_TOKEN},
        timeout=10
    )
    resp.raise_for_status()
    return resp.json()["iamToken"]

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    method = event.get('httpMethod', 'GET')
    
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': '',
            'isBase64Encoded': False
        }
    
    try:
        iam_token = get_iam_token()
        headers = {"Authorization": f"Bearer {iam_token}"}
        
        # 1. Получаем список облаков
        clouds_resp = requests.get(
            "https://resource-manager.api.cloud.yandex.net/resource-manager/v1/clouds",
            headers=headers,
            timeout=10
        )
        clouds_resp.raise_for_status()
        clouds = clouds_resp.json().get("clouds", [])
        if not clouds:
            return error_response(404, "Облака не найдены. Проверьте права токена.")
        
        cloud_id = clouds[0]["id"]

        # 2. Получаем список папок в первом облаке
        folders_resp = requests.get(
            f"https://resource-manager.api.cloud.yandex.net/resource-manager/v1/folders?cloudId={cloud_id}",
            headers=headers,
            timeout=10
        )
        folders_resp.raise_for_status()
        folders = folders_resp.json().get("folders", [])
        if not folders:
            return error_response(404, f"Папки в облаке {cloud_id} не найдены.")
        
        folder_id = folders[0]["id"]

        # 3. Получаем список VM
        vms_resp = requests.get(
            f"https://compute.api.cloud.yandex.net/compute/v1/instances?folderId={folder_id}",
            headers=headers,
            timeout=10
        )
        vms = vms_resp.json().get("instances", [])
        
        # 4. Получаем список Функций
        funcs_resp = requests.get(
            f"https://serverless-functions.api.cloud.yandex.net/functions/v1/functions?folderId={folder_id}",
            headers=headers,
            timeout=10
        )
        funcs = funcs_resp.json().get("functions", [])
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'resources': {
                    'vms': {'count': len(vms)},
                    'functions': {'count': len(funcs)}
                },
                'cloud_info': {
                    'cloud_id': cloud_id,
                    'folder_id': folder_id,
                    'active_vms': len(vms),
                    'active_functions': len(funcs)
                }
            }),
            'isBase64Encoded': False
        }

    except Exception as e:
        return error_response(500, f"Критическая ошибка: {str(e)}")

def error_response(status_code: int, message: str) -> Dict[str, Any]:
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({'error': message, 'success': False}),
        'isBase64Encoded': False
    }
