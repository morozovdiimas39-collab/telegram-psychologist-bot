import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor


def handler(event: dict, context) -> dict:
    """Получить SSH приватный ключ для конкретной VM"""
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
        dsn = os.environ['DATABASE_URL']
        schema = os.environ.get('MAIN_DB_SCHEMA', 'public')
        
        conn = psycopg2.connect(dsn)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query_params = event.get('queryStringParameters') or {}
        vm_id = query_params.get('id')
        
        if not vm_id:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Укажи id VM'}),
                'isBase64Encoded': False
            }
        
        # Получаем SSH ключ и информацию о VM
        cur.execute(
            f"""
            SELECT id, name, ip_address, ssh_user, ssh_private_key, status
            FROM {schema}.vm_instances 
            WHERE id = %s
            """,
            (vm_id,)
        )
        vm = cur.fetchone()
        
        if not vm:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'VM не найдена'}),
                'isBase64Encoded': False
            }
        
        if not vm['ssh_private_key']:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'SSH ключ не найден для этой VM'}),
                'isBase64Encoded': False
            }
        
        cur.close()
        conn.close()
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'vm_id': vm['id'],
                'name': vm['name'],
                'ip_address': vm['ip_address'],
                'ssh_user': vm['ssh_user'],
                'ssh_private_key': vm['ssh_private_key'],
                'status': vm['status']
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
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
