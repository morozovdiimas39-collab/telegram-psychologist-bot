import json
import os
import urllib.request
from typing import Dict, Any

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Установка webhook для Telegram бота
    Вызовите эту функцию один раз для настройки бота
    """
    method = event.get('httpMethod', 'GET')
    
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Max-Age': '86400'
            },
            'body': '',
            'isBase64Encoded': False
        }
    
    bot_token = os.environ['TELEGRAM_BOT_TOKEN']
    
    # URL webhook - адрес функции telegram-bot
    webhook_url = "https://functions.poehali.dev/3191b551-a958-4467-b19b-b8dad21e8b7e"
    
    if method == 'GET':
        # Установка webhook
        telegram_url = f'https://api.telegram.org/bot{bot_token}/setWebhook'
        
        payload = {
            'url': webhook_url,
            'allowed_updates': ['message']
        }
        
        try:
            req = urllib.request.Request(
                telegram_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if result.get('ok'):
                    return {
                        'statusCode': 200,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'success': True,
                            'message': f'✅ Webhook установлен на {webhook_url}',
                            'result': result
                        }),
                        'isBase64Encoded': False
                    }
                else:
                    return {
                        'statusCode': 400,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'success': False,
                            'message': 'Ошибка установки webhook',
                            'error': result
                        }),
                        'isBase64Encoded': False
                    }
        
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'message': 'Ошибка при запросе к Telegram API',
                    'error': str(e)
                }),
                'isBase64Encoded': False
            }
    
    elif method == 'DELETE':
        # Удаление webhook
        telegram_url = f'https://api.telegram.org/bot{bot_token}/deleteWebhook'
        
        try:
            req = urllib.request.Request(telegram_url)
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'success': True,
                        'message': 'Webhook удален',
                        'result': result
                    }),
                    'isBase64Encoded': False
                }
        
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'message': 'Ошибка при удалении webhook',
                    'error': str(e)
                }),
                'isBase64Encoded': False
            }
    
    return {
        'statusCode': 405,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({'error': 'Method not allowed'}),
        'isBase64Encoded': False
    }
