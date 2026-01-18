import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor


def handler(event: dict, context) -> dict:
    """Подготовка информации для деплоя (реальный деплой через GitHub Actions или webhook)"""
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
        body_str = event.get('body', '{}')
        if not body_str or body_str == '':
            body_str = '{}'
        body = json.loads(body_str) if isinstance(body_str, str) else body_str
        
        config_name = body.get('config_name')
        deploy_type = body.get('type', 'all')
        
        if not config_name:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Укажи config_name'}),
                'isBase64Encoded': False
            }
        
        dsn = os.environ['DATABASE_URL']
        schema = os.environ.get('MAIN_DB_SCHEMA', 'public')
        
        conn = psycopg2.connect(dsn)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute(
            f"""
            SELECT dc.*, vm.ip_address, vm.name as vm_name
            FROM {schema}.deploy_configs dc
            LEFT JOIN {schema}.vm_instances vm ON dc.vm_instance_id = vm.id
            WHERE dc.name = %s
            """,
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
        
        logs = [
            f"🚀 Подготовка деплоя: {deploy_type}",
            f"📦 Проект: {config['domain']}",
            f"🖥️  Репозиторий: {config['github_repo']}",
            ""
        ]
        
        if config['vm_instance_id'] and config['ip_address']:
            logs.append(f"✅ VM сервер: {config['vm_name']} ({config['ip_address']})")
            logs.append("")
            logs.append("📝 Для полного деплоя используй:")
            logs.append("  1. GitHub Actions (автоматический деплой при пуше)")
            logs.append("  2. Webhook server на VM (принимает команды деплоя)")
            logs.append("  3. Прямой SSH доступ к серверу")
        else:
            logs.append("⚠️  VM не привязана к конфигу")
            logs.append("Создай VM и привяжи её к конфигу")
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'success': True,
                'logs': logs,
                'config': dict(config),
                'deploy_type': deploy_type
            }, default=str),
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
