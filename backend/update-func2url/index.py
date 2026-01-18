import json
import os
import requests


def handler(event: dict, context) -> dict:
    """Обновляет func2url.json с новыми URL функций и коммитит в GitHub"""
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
        function_urls = body.get('function_urls', {})
        github_repo = body.get('github_repo')
        github_token = os.environ.get('GITHUB_TOKEN')
        
        logs = []
        
        if not github_repo or not github_token:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'github_repo и GITHUB_TOKEN обязательны'}),
                'isBase64Encoded': False
            }
        
        logs.append(f"📦 Обновляю func2url.json для {github_repo}")
        
        # Получаем текущий func2url.json из репозитория
        headers = {
            'Authorization': f'Bearer {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        file_path = 'backend/func2url.json'
        url = f'https://api.github.com/repos/{github_repo}/contents/{file_path}'
        
        logs.append("📥 Читаю текущий func2url.json...")
        get_resp = requests.get(url, headers=headers, timeout=10)
        
        current_func2url = {}
        file_sha = None
        
        if get_resp.status_code == 200:
            file_data = get_resp.json()
            file_sha = file_data['sha']
            import base64
            content = base64.b64decode(file_data['content']).decode('utf-8')
            current_func2url = json.loads(content)
            logs.append(f"✓ Найдено {len(current_func2url)} существующих URL")
        else:
            logs.append("⚠️ func2url.json не найден, создаю новый")
        
        # Обновляем URL
        updated_count = 0
        for func_name, new_url in function_urls.items():
            if current_func2url.get(func_name) != new_url:
                current_func2url[func_name] = new_url
                updated_count += 1
                logs.append(f"  ✓ {func_name}: {new_url}")
        
        if updated_count == 0:
            logs.append("✓ Нет изменений в func2url.json")
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'success': True, 'updated': 0, 'logs': logs}),
                'isBase64Encoded': False
            }
        
        # Сохраняем обновлённый файл
        logs.append(f"💾 Сохраняю {updated_count} изменений...")
        
        new_content = json.dumps(current_func2url, indent=2, ensure_ascii=False)
        import base64
        encoded_content = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')
        
        commit_data = {
            'message': f'chore: update func2url.json with {updated_count} new URLs',
            'content': encoded_content,
            'branch': 'main'
        }
        
        if file_sha:
            commit_data['sha'] = file_sha
        
        put_resp = requests.put(url, headers=headers, json=commit_data, timeout=15)
        
        if put_resp.status_code in [200, 201]:
            logs.append("✅ func2url.json обновлён и закоммичен в GitHub!")
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'success': True,
                    'updated': updated_count,
                    'func2url': current_func2url,
                    'logs': logs
                }),
                'isBase64Encoded': False
            }
        else:
            error_msg = put_resp.json().get('message', 'Unknown error')
            logs.append(f"❌ Ошибка коммита: {error_msg}")
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': error_msg, 'logs': logs}),
                'isBase64Encoded': False
            }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e), 'logs': logs if 'logs' in locals() else []}),
            'isBase64Encoded': False
        }
