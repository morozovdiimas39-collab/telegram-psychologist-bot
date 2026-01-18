import json
import os
import requests


def handler(event: dict, context) -> dict:
    """Деплой фронтенда через webhook на VM"""
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
        domain = body.get('domain', '').strip()
        github_repo = body.get('github_repo', '').strip()
        
        if not domain or not github_repo:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'domain и github_repo обязательны'}),
                'isBase64Encoded': False
            }
        
        webhook_url = os.environ.get('VM_WEBHOOK_URL')
        
        if not webhook_url:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'VM_WEBHOOK_URL не настроен'}),
                'isBase64Encoded': False
            }
        
        # Отправляем webhook на VM
        response = requests.post(
            webhook_url,
            json={
                'domain': domain,
                'github_repo': github_repo
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'success': True,
                    'message': f'Деплой запущен для {domain}',
                    'details': result
                }),
                'isBase64Encoded': False
            }
        else:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'error': f'Ошибка webhook: {response.text}'
                }),
                'isBase64Encoded': False
            }
        
    except requests.Timeout:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Timeout - VM не отвечает'}),
            'isBase64Encoded': False
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)}),
            'isBase64Encoded': False
        }
