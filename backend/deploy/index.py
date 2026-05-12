import json
import os
import re
import psycopg2
from psycopg2.extras import RealDictCursor
import requests


def handler(event: dict, context) -> dict:
    """Деплой проекта на VM через webhook"""
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
        
        if not config_name:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Укажи config_name'}),
                'isBase64Encoded': False
            }
        
        dsn = os.environ['DATABASE_URL']
        schema = os.environ.get('MAIN_DB_SCHEMA', 'public')
        github_token = os.environ.get('GITHUB_TOKEN')
        
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
            f"🚀 Деплой: {config['domain']}",
            f"📦 Репо: {config['github_repo']}",
            ""
        ]
        
        if not config['vm_instance_id'] or not config['ip_address']:
            logs.append("❌ VM не привязана к конфигу")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'VM не привязана', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        vm_ip = config['ip_address']
        domain = config['domain']
        github_repo = (config['github_repo'] or '').strip().rstrip('/').rstrip('.git')
        project_name = config_name  # имя конфига = имя проекта на VM (/opt/{project_name})
        
        # Webhook ожидает: github_url, project_name, domain, secrets (deploy-project.py)
        if github_repo.startswith('http://') or github_repo.startswith('https://'):
            match = re.search(r'github\.com[/:]([^/]+/[^/]+?)(?:\.git)?/?$', github_repo)
            repo_part = match.group(1) if match else github_repo
        else:
            repo_part = github_repo
        github_url = f"https://{github_token}@github.com/{repo_part}.git" if github_token else f"https://github.com/{repo_part}.git"
        
        logs.append(f"🖥️  Сервер: {vm_ip}")
        logs.append("")
        
        # Отправляем команду деплоя на webhook VM
        webhook_url = f"http://{vm_ip}:9000/deploy"
        logs.append(f"🚀 Отправляю команду деплоя...")
        
        try:
            deploy_resp = requests.post(
                webhook_url,
                json={
                    'github_url': github_url,
                    'project_name': project_name,
                    'domain': domain,
                    'secrets': []
                },
                timeout=5
            )
            
            if deploy_resp.status_code == 200:
                logs.append("✅ Команда деплоя отправлена!")
                logs.append("")
                logs.append("⏳ Деплой запущен на сервере")
                logs.append(f"   Подожди 1-2 минуты, проект собирается...")
                logs.append(f"   Сайт будет доступен: http://{domain}")
                logs.append(f"   Или по IP: http://{vm_ip}")
                
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({
                        'success': True,
                        'logs': logs,
                        'url': f"http://{domain}",
                        'ip_url': f"http://{vm_ip}"
                    }),
                    'isBase64Encoded': False
                }
            else:
                logs.append(f"❌ Webhook ошибка: {deploy_resp.text[:200]}")
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Webhook failed', 'logs': logs}),
                    'isBase64Encoded': False
                }
                
        except requests.exceptions.Timeout:
            logs.append("❌ Webhook не отвечает (timeout)")
            logs.append("")
            logs.append("💡 Возможные причины:")
            logs.append("   1. VM ещё не готова (подожди 3-5 минут после создания)")
            logs.append("   2. Webhook сервер не запущен")
            logs.append("   3. Это старая VM - создай новую через 'Создать VM'")
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Webhook timeout', 'logs': logs}),
                'isBase64Encoded': False
            }
        except Exception as e:
            logs.append(f"❌ Ошибка: {str(e)}")
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': str(e), 'logs': logs}),
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
