import json
import os
import psycopg2
import requests
from psycopg2.extras import RealDictCursor


def handler(event: dict, context) -> dict:
    """Деплой фронтенда через webhook на VM (данные из deploy_configs)"""
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
        config_name = body.get('config_name', 'production')
        
        dsn = os.environ['DATABASE_URL']
        schema = os.environ.get('MAIN_DB_SCHEMA', 'public')
        
        conn = psycopg2.connect(dsn)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute(
            f"SELECT domain, github_repo, vm_webhook_url FROM {schema}.deploy_configs WHERE name = %s",
            (config_name,)
        )
        
        config = cur.fetchone()
        cur.close()
        conn.close()
        
        if not config:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'Конфиг {config_name} не найден'}),
                'isBase64Encoded': False
            }
        
        webhook_url = config['vm_webhook_url']
        domain = config['domain']
        github_repo = config['github_repo']
        
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
    except KeyError as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': f'Секрет не найден: {str(e)}'}),
            'isBase64Encoded': False
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)}),
            'isBase64Encoded': False
        }
