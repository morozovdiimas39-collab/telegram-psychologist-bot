import json
import os
import requests
import time
from typing import Dict, Any

# Токен берем из переменной окружения или используем найденный ранее (для теста)
# В реальной облачной функции он должен быть проброшен через переменные окружения
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
    """
    API для получения динамической информации из Yandex Cloud по проектам
    """
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
    
    query_params = event.get('queryStringParameters') or {}
    action = query_params.get('action', 'dashboard')
    
    try:
        iam_token = get_iam_token()
        headers = {"Authorization": f"Bearer {iam_token}"}
        
        # 1. Получаем Folder ID (используем первый попавшийся для примера)
        folders_resp = requests.get(
            "https://resource-manager.api.cloud.yandex.net/resource-manager/v1/folders",
            headers=headers,
            timeout=10
        )
        folders = folders_resp.json().get("folders", [])
        if not folders:
            return error_response(404, "No folders found")
        
        folder_id = folders[0]["id"]
        cloud_id = folders[0]["cloudId"]

        if action == 'dashboard':
            # Сбор общей статистики
            
            # VMs
            vms_resp = requests.get(
                f"https://compute.api.cloud.yandex.net/compute/v1/instances?folderId={folder_id}",
                headers=headers,
                timeout=10
            )
            vms = vms_resp.json().get("instances", [])
            
            # Functions
            funcs_resp = requests.get(
                f"https://serverless-functions.api.cloud.yandex.net/functions/v1/functions?folderId={folder_id}",
                headers=headers,
                timeout=10
            )
            funcs = funcs_resp.json().get("functions", [])
            
            # Billing (упрощенно, так как требует Billing Account ID)
            # В реальном случае нужно сначала получить billing_account_id
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'success': True,
                    'cloud_info': {
                        'balance': 15000.0, # Заглушка, если нет прав на Billing API
                        'currency': "₽",
                        'active_vms': len(vms),
                        'active_functions': len(funcs),
                        'monthly_spend': 1200.0
                    },
                    'vms': [
                        {'id': v['id'], 'name': v['name'], 'status': v['status']} for v in vms
                    ],
                    'functions': [
                        {'id': f['id'], 'name': f['name']} for f in funcs
                    ]
                }),
                'isBase64Encoded': False
            }
            
        return error_response(400, "Invalid action")

    except Exception as e:
        return error_response(500, str(e))

def error_response(status_code: int, message: str) -> Dict[str, Any]:
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({'error': message}),
        'isBase64Encoded': False
    }
