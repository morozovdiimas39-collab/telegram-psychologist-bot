import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor


def handler(event: dict, context) -> dict:
    """CRUD для конфигураций деплоя: создание, чтение, обновление, удаление"""
    method = event.get('httpMethod', 'GET')

    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
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
        
        # GET - получить все конфиги или один по имени
        if method == 'GET':
            query_params = event.get('queryStringParameters') or {}
            name = query_params.get('name')
            
            if name:
                cur.execute(
                    f"SELECT id, name, domain, github_repo, vm_instance_id, created_at, updated_at FROM {schema}.deploy_configs WHERE name = %s",
                    (name,)
                )
                config = cur.fetchone()
                
                if not config:
                    return {
                        'statusCode': 404,
                        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                        'body': json.dumps({'error': 'Конфиг не найден'}),
                        'isBase64Encoded': False
                    }
                
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps(dict(config), default=str),
                    'isBase64Encoded': False
                }
            else:
                cur.execute(
                    f"SELECT id, name, domain, github_repo, vm_instance_id, created_at, updated_at FROM {schema}.deploy_configs ORDER BY created_at DESC"
                )
                configs = cur.fetchall()
                
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps([dict(c) for c in configs], default=str),
                    'isBase64Encoded': False
                }
        
        # POST - создать новый конфиг
        elif method == 'POST':
            body = json.loads(event.get('body', '{}'))
            
            required = ['name', 'domain', 'github_repo', 'vm_instance_id']
            missing = [f for f in required if not body.get(f)]
            
            if missing:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': f'Обязательные поля: {", ".join(missing)}'}),
                    'isBase64Encoded': False
                }
            
            cur.execute(
                f"""
                INSERT INTO {schema}.deploy_configs 
                (name, domain, github_repo, vm_instance_id, vm_ip, vm_user, vm_ssh_key)
                VALUES (%s, %s, %s, %s, '0.0.0.0', 'ubuntu', 'placeholder')
                RETURNING id, name, domain, github_repo, vm_instance_id, created_at, updated_at
                """,
                (
                    body['name'],
                    body['domain'],
                    body['github_repo'],
                    body['vm_instance_id']
                )
            )
            
            config = cur.fetchone()
            conn.commit()
            
            return {
                'statusCode': 201,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps(dict(config), default=str),
                'isBase64Encoded': False
            }
        
        # PUT - обновить конфиг
        elif method == 'PUT':
            body = json.loads(event.get('body', '{}'))
            old_name = body.get('old_name')
            new_name = body.get('name', old_name)
            
            if not old_name:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Укажи old_name конфига'}),
                    'isBase64Encoded': False
                }
            
            # Строим SET часть запроса
            updates = []
            params = []
            
            if new_name and new_name != old_name:
                updates.append("name = %s")
                params.append(new_name)
            
            for field in ['domain', 'github_repo', 'vm_instance_id']:
                if field in body:
                    updates.append(f"{field} = %s")
                    params.append(body[field])
            
            if not updates:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Нет полей для обновления'}),
                    'isBase64Encoded': False
                }
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(old_name)
            
            cur.execute(
                f"""
                UPDATE {schema}.deploy_configs 
                SET {', '.join(updates)}
                WHERE name = %s
                RETURNING id, name, domain, github_repo, vm_instance_id, created_at, updated_at
                """,
                params
            )
            
            config = cur.fetchone()
            conn.commit()
            
            if not config:
                return {
                    'statusCode': 404,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Конфиг не найден'}),
                    'isBase64Encoded': False
                }
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps(dict(config), default=str),
                'isBase64Encoded': False
            }
        
        # DELETE - удалить конфиг
        elif method == 'DELETE':
            query_params = event.get('queryStringParameters') or {}
            name = query_params.get('name')
            
            if not name:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Укажи name конфига'}),
                    'isBase64Encoded': False
                }
            
            cur.execute(
                f"DELETE FROM {schema}.deploy_configs WHERE name = %s RETURNING id",
                (name,)
            )
            
            deleted = cur.fetchone()
            conn.commit()
            
            if not deleted:
                return {
                    'statusCode': 404,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Конфиг не найден'}),
                    'isBase64Encoded': False
                }
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'success': True, 'message': f'Конфиг {name} удалён'}),
                'isBase64Encoded': False
            }
        
        else:
            return {
                'statusCode': 405,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Метод не поддерживается'}),
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