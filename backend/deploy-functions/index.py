import json
import os
import requests
import base64
import time
from pathlib import Path


def handler(event: dict, context) -> dict:
    """Деплой backend функций из GitHub в Yandex Cloud Functions"""
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
        github_url = body.get('github_url')
        secrets = body.get('secrets', [])
        
        if not github_url:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'github_url required'}),
                'isBase64Encoded': False
            }
        
        oauth_token = os.environ.get('YANDEX_CLOUD_TOKEN')
        logs = []
        
        # Получаем IAM токен
        logs.append("🔐 Получаю IAM токен...")
        iam_resp = requests.post(
            "https://iam.api.cloud.yandex.net/iam/v1/tokens",
            json={"yandexPassportOauthToken": oauth_token},
            timeout=10
        )
        iam_token = iam_resp.json()["iamToken"]
        headers = {"Authorization": f"Bearer {iam_token}"}
        
        # Получаем folder_id
        logs.append("☁️ Получаю folder...")
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
        
        # Получаем список функций из GitHub
        logs.append("📦 Читаю backend из GitHub...")
        repo_parts = github_url.replace('https://github.com/', '').replace('.git', '').split('/')
        owner, repo = repo_parts[0], repo_parts[1]
        
        gh_api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/backend"
        gh_resp = requests.get(gh_api_url, timeout=10)
        
        if gh_resp.status_code != 200:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Backend folder not found in repo', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        backend_items = gh_resp.json()
        function_dirs = [item['name'] for item in backend_items if item['type'] == 'dir']
        
        logs.append(f"✅ Найдено функций: {len(function_dirs)}")
        
        deployed_functions = []
        
        # Деплоим каждую функцию
        for func_name in function_dirs:
            logs.append(f"🚀 Деплою функцию: {func_name}")
            
            # Получаем index.py
            index_url = f"https://api.github.com/repos/{owner}/{repo}/contents/backend/{func_name}/index.py"
            index_resp = requests.get(index_url, timeout=10)
            
            if index_resp.status_code != 200:
                logs.append(f"⚠️ Пропускаю {func_name} - нет index.py")
                continue
            
            index_content = base64.b64decode(index_resp.json()['content']).decode('utf-8')
            
            # Получаем requirements.txt если есть
            requirements = ""
            req_url = f"https://api.github.com/repos/{owner}/{repo}/contents/backend/{func_name}/requirements.txt"
            req_resp = requests.get(req_url, timeout=10)
            if req_resp.status_code == 200:
                requirements = base64.b64decode(req_resp.json()['content']).decode('utf-8')
            
            # Создаём zip с функцией
            import zipfile
            from io import BytesIO
            
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.writestr('index.py', index_content)
                if requirements:
                    zip_file.writestr('requirements.txt', requirements)
            
            zip_content = zip_buffer.getvalue()
            
            # Создаём функцию в Yandex Cloud
            function_payload = {
                "folderId": folder_id,
                "name": func_name,
                "description": f"Function {func_name} from {github_url}"
            }
            
            create_func_resp = requests.post(
                "https://serverless-functions.api.cloud.yandex.net/functions/v1/functions",
                headers={**headers, "Content-Type": "application/json"},
                json=function_payload,
                timeout=30
            )
            
            if create_func_resp.status_code == 409:
                # Функция уже существует, получаем её ID
                list_resp = requests.get(
                    f"https://serverless-functions.api.cloud.yandex.net/functions/v1/functions?folderId={folder_id}",
                    headers=headers,
                    timeout=10
                )
                functions = list_resp.json().get('functions', [])
                function_id = None
                for f in functions:
                    if f['name'] == func_name:
                        function_id = f['id']
                        break
            else:
                function_id = create_func_resp.json()['metadata']['functionId']
            
            # Создаём версию функции
            version_payload = {
                "functionId": function_id,
                "runtime": "python311",
                "entrypoint": "index.handler",
                "resources": {"memory": "134217728"},
                "executionTimeout": "30s",
                "serviceAccountId": None,
                "environment": {}
            }
            
            # Добавляем секреты в environment
            for secret in secrets:
                version_payload['environment'][secret['name']] = secret['value']
            
            # Загружаем код
            version_resp = requests.post(
                f"https://serverless-functions.api.cloud.yandex.net/functions/v1/versions",
                headers={**headers, "Content-Type": "application/json"},
                json={
                    **version_payload,
                    "content": base64.b64encode(zip_content).decode('utf-8')
                },
                timeout=60
            )
            
            if version_resp.status_code not in [200, 201]:
                logs.append(f"❌ Ошибка деплоя {func_name}: {version_resp.text[:200]}")
                continue
            
            # Делаем функцию публичной
            requests.post(
                f"https://serverless-functions.api.cloud.yandex.net/functions/v1/functions/{function_id}:setAccessBindings",
                headers={**headers, "Content-Type": "application/json"},
                json={
                    "accessBindings": [{
                        "roleId": "serverless.functions.invoker",
                        "subject": {"id": "allUsers", "type": "system"}
                    }]
                },
                timeout=10
            )
            
            logs.append(f"✅ {func_name} задеплоена")
            deployed_functions.append(func_name)
        
        logs.append("")
        logs.append(f"🎉 Готово! Задеплоено функций: {len(deployed_functions)}")
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'success': True,
                'deployed': deployed_functions,
                'logs': logs
            }),
            'isBase64Encoded': False
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e), 'logs': logs if 'logs' in locals() else []}),
            'isBase64Encoded': False
        }
