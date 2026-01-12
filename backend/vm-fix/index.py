import json
import os
import requests
import time


def handler(event: dict, context) -> dict:
    """Запустить systemd сервис на VM через Serial Console"""
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
        
        logs = []
        logs.append("🔐 Получаю IAM токен...")
        
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
        logs.append("✅ IAM токен получен")
        
        headers = {"Authorization": f"Bearer {iam_token}"}
        
        logs.append("☁️ Получаю cloud и folder ID...")
        clouds_resp = requests.get(
            "https://resource-manager.api.cloud.yandex.net/resource-manager/v1/clouds",
            headers=headers,
            timeout=10
        )
        
        clouds = clouds_resp.json().get("clouds", [])
        cloud_id = clouds[0]["id"]
        
        folders_resp = requests.get(
            f"https://resource-manager.api.cloud.yandex.net/resource-manager/v1/folders?cloudId={cloud_id}",
            headers=headers,
            timeout=10
        )
        
        folders = folders_resp.json().get("folders", [])
        folder_id = folders[0]["id"]
        
        logs.append("🔍 Ищу VM deploy-server...")
        instances_resp = requests.get(
            f"https://compute.api.cloud.yandex.net/compute/v1/instances?folderId={folder_id}",
            headers=headers,
            timeout=10
        )
        
        instances = instances_resp.json().get("instances", [])
        vm_id = None
        for vm in instances:
            if vm.get("name") == "deploy-server":
                vm_id = vm["id"]
                break
        
        if not vm_id:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'VM не найдена', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        logs.append(f"✅ VM найдена: {vm_id}")
        
        # Обновляем метаданные VM с командой запуска через runcmd
        logs.append("🔧 Обновляю VM metadata для автозапуска...")
        
        # Читаем скрипт деплоя
        script_path = os.path.join(os.path.dirname(__file__), 'deploy_script.py')
        with open(script_path, 'r') as f:
            deploy_script = f.read()
        
        user_data = f"""#cloud-config
write_files:
  - path: /usr/local/bin/deploy_server.py
    permissions: '0755'
    content: |
{chr(10).join('      ' + line for line in deploy_script.split(chr(10)))}

  - path: /etc/systemd/system/deploy-webhook.service
    permissions: '0644'
    content: |
      [Unit]
      Description=Deploy Webhook Server
      After=network.target

      [Service]
      Type=simple
      User=root
      WorkingDirectory=/usr/local/bin
      ExecStart=/usr/bin/python3 /usr/local/bin/deploy_server.py
      Restart=always
      RestartSec=10

      [Install]
      WantedBy=multi-user.target

runcmd:
  - systemctl daemon-reload
  - systemctl enable deploy-webhook
  - systemctl start deploy-webhook
  - sleep 5
  - systemctl status deploy-webhook > /var/log/webhook-status.log
"""
        
        update_payload = {
            "updateMask": "metadata",
            "metadata": {
                "user-data": user_data
            }
        }
        
        update_resp = requests.patch(
            f"https://compute.api.cloud.yandex.net/compute/v1/instances/{vm_id}",
            headers={**headers, "Content-Type": "application/json"},
            json=update_payload,
            timeout=30
        )
        
        if update_resp.status_code not in [200, 202]:
            logs.append(f"⚠️ Не удалось обновить metadata: {update_resp.text}")
        else:
            logs.append("✅ Metadata обновлена")
        
        # Перезагружаем VM
        logs.append("🔄 Перезагружаю VM...")
        restart_resp = requests.post(
            f"https://compute.api.cloud.yandex.net/compute/v1/instances/{vm_id}:restart",
            headers=headers,
            timeout=10
        )
        
        if restart_resp.status_code == 200:
            logs.append("✅ VM перезагружается")
            logs.append("⏳ Systemd сервис запустится автоматически через 2-3 минуты")
            logs.append("💡 Проверь через 3 минуты: http://158.160.115.239:9000/deploy")
        else:
            logs.append(f"⚠️ Ошибка перезагрузки: {restart_resp.text}")
        
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
            'body': json.dumps({'error': str(e), 'logs': logs if 'logs' in locals() else []}),
            'isBase64Encoded': False
        }
