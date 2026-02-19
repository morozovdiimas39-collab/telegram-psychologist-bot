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
            
            # Проверяем наличие новых полей в БД
            try:
                cur.execute(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_schema = %s AND table_name = 'deploy_configs' 
                    AND column_name IN ('database_url', 'database_vm_id')
                """, (schema,))
                existing_columns = {row['column_name'] for row in cur.fetchall()}
                has_database_url = 'database_url' in existing_columns
                has_database_vm_id = 'database_vm_id' in existing_columns
            except:
                has_database_url = False
                has_database_vm_id = False
            
            # Формируем список полей для SELECT
            base_fields = ['id', 'name', 'domain', 'github_repo', 'vm_instance_id', 'created_at', 'updated_at']
            if has_database_url:
                base_fields.append('database_url')
            if has_database_vm_id:
                base_fields.append('database_vm_id')
            
            fields_str = ', '.join(base_fields)
            
            if name:
                cur.execute(
                    f"SELECT {fields_str} FROM {schema}.deploy_configs WHERE name = %s",
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
                
                config_dict = dict(config)
                # Если поля отсутствуют, добавляем null
                if not has_database_url:
                    config_dict['database_url'] = None
                if not has_database_vm_id:
                    config_dict['database_vm_id'] = None
                
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps(config_dict, default=str),
                    'isBase64Encoded': False
                }
            else:
                cur.execute(
                    f"SELECT {fields_str} FROM {schema}.deploy_configs ORDER BY created_at DESC"
                )
                configs = cur.fetchall()
                
                configs_list = [dict(c) for c in configs]
                # Если поля отсутствуют, добавляем null для каждого конфига
                if not has_database_url or not has_database_vm_id:
                    for config in configs_list:
                        if not has_database_url:
                            config['database_url'] = None
                        if not has_database_vm_id:
                            config['database_vm_id'] = None
                
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps(configs_list, default=str),
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
            
            # Проверяем наличие новых полей в БД
            try:
                cur.execute(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_schema = %s AND table_name = 'deploy_configs' 
                    AND column_name IN ('database_url', 'database_vm_id')
                """, (schema,))
                existing_columns = {row['column_name'] for row in cur.fetchall()}
                has_database_url = 'database_url' in existing_columns
                has_database_vm_id = 'database_vm_id' in existing_columns
            except:
                has_database_url = False
                has_database_vm_id = False
            
            if has_database_url and has_database_vm_id:
                cur.execute(
                    f"""
                    INSERT INTO {schema}.deploy_configs 
                    (name, domain, github_repo, vm_instance_id, database_url, database_vm_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, name, domain, github_repo, vm_instance_id, database_url, database_vm_id, created_at, updated_at
                    """,
                    (
                        body['name'],
                        body['domain'],
                        body['github_repo'],
                        body.get('vm_instance_id'),
                        body.get('database_url'),
                        body.get('database_vm_id')
                    )
                )
            elif has_database_url:
                cur.execute(
                    f"""
                    INSERT INTO {schema}.deploy_configs 
                    (name, domain, github_repo, vm_instance_id, database_url)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, name, domain, github_repo, vm_instance_id, database_url, created_at, updated_at
                    """,
                    (
                        body['name'],
                        body['domain'],
                        body['github_repo'],
                        body['vm_instance_id'],
                        body.get('database_url')  # Опционально
                    )
                )
            else:
                cur.execute(
                    f"""
                    INSERT INTO {schema}.deploy_configs 
                    (name, domain, github_repo, vm_instance_id)
                    VALUES (%s, %s, %s, %s)
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
            
            config_dict = dict(config)
            if not has_database_url:
                config_dict['database_url'] = None
            if not has_database_vm_id:
                config_dict['database_vm_id'] = None
            
            return {
                'statusCode': 201,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps(config_dict, default=str),
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
            
            # Проверяем наличие новых полей в БД
            try:
                cur.execute(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_schema = %s AND table_name = 'deploy_configs' 
                    AND column_name IN ('database_url', 'database_vm_id')
                """, (schema,))
                existing_columns = {row['column_name'] for row in cur.fetchall()}
                has_database_url = 'database_url' in existing_columns
                has_database_vm_id = 'database_vm_id' in existing_columns
            except:
                has_database_url = False
                has_database_vm_id = False
            
            # Строим SET часть запроса
            updates = []
            params = []
            
            if new_name and new_name != old_name:
                updates.append("name = %s")
                params.append(new_name)
            
            allowed_fields = ['domain', 'github_repo', 'vm_instance_id']
            if has_database_url:
                allowed_fields.append('database_url')
            if has_database_vm_id:
                allowed_fields.append('database_vm_id')
            
            for field in allowed_fields:
                if field in body:
                    value = body[field]
                    if value is None or value == '' or (isinstance(value, str) and value.strip() == ''):
                        updates.append(f"{field} = NULL")
                    else:
                        updates.append(f"{field} = %s")
                        params.append(value)
            
            if not updates:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Нет полей для обновления'}),
                    'isBase64Encoded': False
                }
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(old_name)
            
            # Формируем список полей для RETURNING
            base_return_fields = ['id', 'name', 'domain', 'github_repo', 'vm_instance_id', 'created_at', 'updated_at']
            if has_database_url:
                base_return_fields.append('database_url')
            if has_database_vm_id:
                base_return_fields.append('database_vm_id')
            return_fields = base_return_fields
            
            return_fields_str = ', '.join(return_fields)
            
            cur.execute(
                f"""
                UPDATE {schema}.deploy_configs 
                SET {', '.join(updates)}
                WHERE name = %s
                RETURNING {return_fields_str}
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
            
            config_dict = dict(config)
            if not has_database_url:
                config_dict['database_url'] = None
            if not has_database_vm_id:
                config_dict['database_vm_id'] = None
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps(config_dict, default=str),
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