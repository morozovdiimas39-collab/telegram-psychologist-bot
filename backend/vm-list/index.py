import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import requests


def handler(event: dict, context) -> dict:
    """Получить список всех VM инстансов"""
    method = event.get('httpMethod', 'GET')

    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, DELETE, OPTIONS',
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
        
        if method == 'GET':
            query_params = event.get('queryStringParameters') or {}
            vm_id = query_params.get('id')
            
            if vm_id:
                # Получить конкретную VM
                cur.execute(
                    f"""
                    SELECT id, name, ip_address, ssh_user, status, yandex_vm_id, created_at, updated_at
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
                
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps(dict(vm), default=str),
                    'isBase64Encoded': False
                }
            else:
                # Получить все VM (кроме удалённых)
                cur.execute(
                    f"""
                    SELECT id, name, ip_address, ssh_user, status, yandex_vm_id, created_at, updated_at
                    FROM {schema}.vm_instances 
                    WHERE status != 'deleted'
                    ORDER BY created_at DESC
                    """
                )
                vms = cur.fetchall()
                
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps([dict(vm) for vm in vms], default=str),
                    'isBase64Encoded': False
                }
        
        elif method == 'DELETE':
            # Удалить VM из Yandex Cloud и БД
            try:
                query_params = event.get('queryStringParameters') or {}
                vm_id = query_params.get('id')
                
                if not vm_id:
                    cur.close()
                    conn.close()
                    return {
                        'statusCode': 400,
                        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                        'body': json.dumps({'error': 'Укажи id VM'}),
                        'isBase64Encoded': False
                    }
                
                # Получаем информацию о VM из БД
                cur.execute(
                    f"""
                    SELECT id, name, yandex_vm_id, status, ip_address
                    FROM {schema}.vm_instances 
                    WHERE id = %s
                    """,
                    (vm_id,)
                )
                vm = cur.fetchone()
                
                if not vm:
                    cur.close()
                    conn.close()
                    return {
                        'statusCode': 404,
                        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                        'body': json.dumps({'error': 'VM не найдена'}),
                        'isBase64Encoded': False
                    }
                
                vm_name = vm.get('name', 'Unknown')
                vm_yandex_id = vm.get('yandex_vm_id')
                vm_ip = vm.get('ip_address')
                
                logs = []
                logs.append(f"🗑️ Удаление VM: {vm_name} (ID: {vm_id})")
                
                # Удаляем из Yandex Cloud, если есть yandex_vm_id
                if vm_yandex_id:
                    try:
                        # Получаем IAM токен
                        oauth_token = os.environ.get('YANDEX_CLOUD_TOKEN')
                        if not oauth_token:
                            logs.append("⚠️ YANDEX_CLOUD_TOKEN не настроен, пропускаю удаление из YC")
                        else:
                            iam_resp = requests.post(
                                'https://iam.api.cloud.yandex.net/iam/v1/tokens',
                                json={'yandexPassportOauthToken': oauth_token},
                                timeout=10
                            )
                            
                            if iam_resp.status_code == 200:
                                iam_token = iam_resp.json().get('iamToken')
                                if not iam_token:
                                    logs.append("⚠️ Не удалось получить IAM токен из ответа")
                                else:
                                    headers = {'Authorization': f'Bearer {iam_token}'}
                                    
                                    logs.append(f"☁️ Удаляю VM из Yandex Cloud: {vm_yandex_id}")
                                    
                                    # Удаляем VM из Yandex Cloud
                                    delete_resp = requests.delete(
                                        f'https://compute.api.cloud.yandex.net/compute/v1/instances/{vm_yandex_id}',
                                        headers=headers,
                                        timeout=30
                                    )
                                    
                                    if delete_resp.status_code in [200, 201, 202]:
                                        try:
                                            response_data = delete_resp.json()
                                            operation_id = response_data.get('id')
                                            logs.append(f"✅ Операция удаления запущена: {operation_id}")
                                            logs.append("⏳ Операция выполняется асинхронно в Yandex Cloud")
                                        except:
                                            logs.append("✅ Запрос на удаление отправлен в Yandex Cloud")
                                    elif delete_resp.status_code == 404:
                                        logs.append("⚠️ VM уже удалена из Yandex Cloud")
                                    else:
                                        error_text = delete_resp.text[:200] if delete_resp.text else 'Нет текста ошибки'
                                        logs.append(f"⚠️ Ошибка удаления из YC: {delete_resp.status_code} - {error_text}")
                            else:
                                error_text = iam_resp.text[:200] if iam_resp.text else 'Нет текста ошибки'
                                logs.append(f"⚠️ Ошибка получения IAM токена: {iam_resp.status_code} - {error_text}")
                    except Exception as e:
                        import traceback
                        error_msg = str(e)[:200]
                        logs.append(f"⚠️ Ошибка при удалении из YC: {error_msg}")
                        print(f"Error deleting from YC: {traceback.format_exc()}")
                else:
                    logs.append("ℹ️ VM не привязана к Yandex Cloud (нет yandex_vm_id)")
                
                # Удаляем из БД
                logs.append("🗄️ Удаляю запись из БД...")
                cur.execute(
                    f"DELETE FROM {schema}.vm_instances WHERE id = %s RETURNING id",
                    (vm_id,)
                )
                
                deleted = cur.fetchone()
                conn.commit()
                cur.close()
                conn.close()
                
                if not deleted:
                    return {
                        'statusCode': 404,
                        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                        'body': json.dumps({'error': 'VM не найдена в БД', 'logs': logs}),
                        'isBase64Encoded': False
                    }
                
                logs.append("✅ VM успешно удалена")
                
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({
                        'success': True,
                        'message': f'VM {vm_name} удалена',
                        'logs': logs,
                        'vm_name': vm_name,
                        'vm_ip': vm_ip
                    }),
                    'isBase64Encoded': False
                }
            except Exception as delete_error:
                # Закрываем соединения в случае ошибки
                if 'cur' in locals():
                    try:
                        cur.close()
                    except:
                        pass
                if 'conn' in locals():
                    try:
                        conn.close()
                    except:
                        pass
                
                import traceback
                error_details = traceback.format_exc()
                print(f"ERROR in DELETE method: {str(delete_error)}")
                print(f"Traceback: {error_details}")
                
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({
                        'error': str(delete_error),
                        'details': error_details
                    }),
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
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR in vm-list: {str(e)}")
        print(f"Traceback: {error_details}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': str(e),
                'details': error_details if 'error_details' in locals() else None
            }),
            'isBase64Encoded': False
        }
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()