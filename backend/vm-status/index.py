import json
import os
import requests


def handler(event: dict, context) -> dict:
    """Проверить статус деплоя на VM"""
    method = event.get('httpMethod', 'GET')

    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': '',
            'isBase64Encoded': False
        }

    try:
        vm_webhook = os.environ.get('VM_WEBHOOK_URL')
        
        if not vm_webhook:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'VM_WEBHOOK_URL not configured'}),
                'isBase64Encoded': False
            }
        
        # Проверяем доступность webhook
        logs = []
        logs.append(f"🔍 Проверяю webhook: {vm_webhook}")
        
        try:
            response = requests.get(vm_webhook.replace('/deploy', '/'), timeout=5)
            logs.append(f"✅ Webhook доступен (статус: {response.status_code})")
        except Exception as e:
            logs.append(f"❌ Webhook недоступен: {str(e)}")
            logs.append("💡 VM может быть не запущена или скрипт не работает")
        
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
            'body': json.dumps({'error': str(e)}),
            'isBase64Encoded': False
        }
