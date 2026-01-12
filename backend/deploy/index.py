import json
import os
import requests
from typing import Dict, List


def handler(event: dict, context) -> dict:
    """
    API для приёма заявок на деплой проектов.
    Отправляет webhook на сервер деплоя или сохраняет в очередь.
    """
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

    if method != 'POST':
        return {
            'statusCode': 405,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Method not allowed'}),
            'isBase64Encoded': False
        }

    try:
        body = json.loads(event.get('body', '{}'))
        github_url = body.get('githubUrl', '').strip()
        project_name = body.get('projectName', '').strip()
        domain = body.get('domain', '').strip()
        secrets_list = body.get('secrets', [])

        if not github_url or not project_name or not domain:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Missing required fields'}),
                'isBase64Encoded': False
            }

        vm_webhook_url = os.environ.get('VM_WEBHOOK_URL')
        
        logs = []
        logs.append("✅ Заявка получена")
        logs.append(f"📦 Проект: {project_name}")
        logs.append(f"🔗 GitHub: {github_url}")
        logs.append(f"🌐 Домен: {domain}")
        logs.append(f"🔐 Секретов: {len(secrets_list)}")

        if vm_webhook_url:
            logs.append("📡 Отправляю запрос на сервер деплоя...")
            try:
                response = requests.post(
                    vm_webhook_url,
                    json={
                        'github_url': github_url,
                        'project_name': project_name,
                        'domain': domain,
                        'secrets': secrets_list
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    logs.append("✅ Деплой запущен на сервере")
                    logs.append("⏳ Процесс может занять 5-10 минут")
                    return {
                        'statusCode': 200,
                        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                        'body': json.dumps({'success': True, 'logs': logs}),
                        'isBase64Encoded': False
                    }
                else:
                    logs.append(f"⚠️ Сервер вернул код: {response.status_code}")
            except requests.RequestException as e:
                logs.append(f"⚠️ Ошибка подключения к серверу: {str(e)}")
        
        logs.append("ℹ️ VM_WEBHOOK_URL не настроен")
        logs.append("💡 Используй скрипт deploy.py локально для ручного деплоя")
        logs.append(f"💡 Команда: python deploy.py --github {github_url} --name {project_name} --domain {domain}")
        
        return {
            'statusCode': 202,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'success': True, 'logs': logs, 'manual_deploy_required': True}),
            'isBase64Encoded': False
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)}),
            'isBase64Encoded': False
        }
