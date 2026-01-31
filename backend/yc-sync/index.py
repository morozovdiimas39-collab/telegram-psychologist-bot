import json
import os
import requests
import psycopg2
from psycopg2.extras import RealDictCursor


def handler(event: dict, context) -> dict:
    """Синхронизация статусов VM из Yandex Cloud в БД"""
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
        oauth_token = os.environ.get('YANDEX_CLOUD_TOKEN')
        dsn = os.environ['DATABASE_URL']
        schema = os.environ.get('MAIN_DB_SCHEMA', 'public')
        
        logs = ["🔄 Синхронизация VM с Yandex Cloud..."]
        
        # Получаем IAM токен
        iam_resp = requests.post(
            "https://iam.api.cloud.yandex.net/iam/v1/tokens",
            json={"yandexPassportOauthToken": oauth_token},
            timeout=10
        )
        
        if iam_resp.status_code != 200:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'IAM error: {iam_resp.text}', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        iam_token = iam_resp.json()["iamToken"]
        headers = {"Authorization": f"Bearer {iam_token}"}
        
        # Получаем cloud и folder
        clouds_resp = requests.get(
            "https://resource-manager.api.cloud.yandex.net/resource-manager/v1/clouds",
            headers=headers,
            timeout=10
        )
        cloud_id = clouds_resp.json()["clouds"][0]["id"]
        
        folders_resp = requests.get(
            f"https://resource-manager.api.cloud.yandex.net/resource-manager/v1/folders?cloudId={cloud_id}",
            headers=headers,
            timeout=10
        )
        folder_id = folders_resp.json()["folders"][0]["id"]
        
        # Получаем все VM из Yandex Cloud
        instances_resp = requests.get(
            f"https://compute.api.cloud.yandex.net/compute/v1/instances?folderId={folder_id}",
            headers=headers,
            timeout=10
        )
        yc_instances = instances_resp.json().get("instances", [])
        
        logs.append(f"📡 Найдено {len(yc_instances)} VM в Yandex Cloud")
        
        # Подключаемся к БД
        conn = psycopg2.connect(dsn)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Получаем все VM из БД
        cur.execute(f"SELECT id, name, yandex_vm_id, status FROM {schema}.vm_instances")
        db_instances = {vm['yandex_vm_id']: vm for vm in cur.fetchall() if vm['yandex_vm_id']}
        
        # Получаем список yandex_vm_id из YC
        yc_vm_ids = {vm['id'] for vm in yc_instances}
        
        updated = 0
        deleted = 0
        
        # Помечаем VM которых нет в YC как удалённые
        for yc_id, db_vm in db_instances.items():
            if yc_id not in yc_vm_ids:
                cur.execute(
                    f"""
                    UPDATE {schema}.vm_instances 
                    SET status = 'deleted', updated_at = CURRENT_TIMESTAMP
                    WHERE yandex_vm_id = %s
                    """,
                    (yc_id,)
                )
                deleted += 1
                logs.append(f"🗑️ VM {db_vm['name']} удалена из YC, помечена как deleted")
        
        # Синхронизируем каждую VM из Yandex Cloud
        for yc_vm in yc_instances:
            yc_id = yc_vm["id"]
            yc_name = yc_vm.get("name", "unknown")
            yc_status = yc_vm.get("status", "UNKNOWN")
            
            # Получаем IP адрес
            vm_ip = None
            for iface in yc_vm.get("networkInterfaces", []):
                nat = iface.get("primaryV4Address", {}).get("oneToOneNat", {})
                vm_ip = nat.get("address")
                if vm_ip:
                    break
            
            # Маппим статус Yandex Cloud -> наш статус
            status_map = {
                "RUNNING": "ready",
                "STOPPED": "stopped",
                "STARTING": "creating",
                "STOPPING": "stopped",
                "PROVISIONING": "creating"
            }
            our_status = status_map.get(yc_status, "unknown")
            
            if yc_id in db_instances:
                # Обновляем существующую VM
                cur.execute(
                    f"""
                    UPDATE {schema}.vm_instances 
                    SET name = %s, ip_address = %s, status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE yandex_vm_id = %s
                    """,
                    (yc_name, vm_ip, our_status, yc_id)
                )
                updated += 1
                logs.append(f"✅ Обновлена VM {yc_name} ({yc_status} → {our_status})")
            else:
                # Добавляем новую VM (с обработкой дубликатов по имени)
                cur.execute(
                    f"""
                    INSERT INTO {schema}.vm_instances 
                    (name, ip_address, ssh_user, status, yandex_vm_id)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (name) DO UPDATE 
                    SET ip_address = EXCLUDED.ip_address,
                        status = EXCLUDED.status,
                        yandex_vm_id = EXCLUDED.yandex_vm_id,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (yc_name, vm_ip, "ubuntu", our_status, yc_id)
                )
                updated += 1
                logs.append(f"➕ Добавлена VM {yc_name}")
        
        conn.commit()
        cur.close()
        conn.close()
        
        logs.append(f"🎉 Синхронизация завершена: обновлено {updated} VM, удалено {deleted} VM")
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'success': True, 'updated': updated, 'deleted': deleted, 'logs': logs}),
            'isBase64Encoded': False
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)}),
            'isBase64Encoded': False
        }