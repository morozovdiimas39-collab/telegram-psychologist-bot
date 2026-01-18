import json
import os
import requests
import base64
import time
from pathlib import Path


def handler(event: dict, context) -> dict:
    """Деплой backend функций из локального проекта в Yandex Cloud Functions"""
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
        secrets = body.get('secrets', [])
        github_repo = body.get('github_repo')
        
        oauth_token = os.environ.get('YANDEX_CLOUD_TOKEN')
        github_token = os.environ.get('GITHUB_TOKEN')
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
        
        # Читаем функции из GitHub репозитория
        if not github_repo or not github_token:
            raise ValueError("github_repo и GITHUB_TOKEN обязательны для чтения функций")
        
        logs.append("📦 Читаю функции из GitHub репозитория...")
        
        headers_gh = {
            'Authorization': f'Bearer {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Получаем список папок в /backend
        backend_url = f'https://api.github.com/repos/{github_repo}/contents/backend'
        backend_resp = requests.get(backend_url, headers=headers_gh, timeout=10)
        
        if backend_resp.status_code != 200:
            raise ValueError(f"Не удалось прочитать /backend: {backend_resp.text[:200]}")
        
        backend_items = backend_resp.json()
        function_dirs = []
        
        for item in backend_items:
            if item['type'] == 'dir':
                # Проверяем наличие index.py
                index_url = f"https://api.github.com/repos/{github_repo}/contents/backend/{item['name']}/index.py"
                index_check = requests.get(index_url, headers=headers_gh, timeout=5)
                if index_check.status_code == 200:
                    function_dirs.append(item['name'])
        
        logs.append(f"✅ Найдено функций: {len(function_dirs)}")
        
        deployed_functions = []
        function_urls = {}
        
        # Деплоим каждую функцию
        for func_name in function_dirs:
            logs.append(f"🚀 Деплою функцию: {func_name}")
            
            # Читаем index.py из GitHub
            index_url = f'https://api.github.com/repos/{github_repo}/contents/backend/{func_name}/index.py'
            index_resp = requests.get(index_url, headers=headers_gh, timeout=10)
            
            if index_resp.status_code != 200:
                logs.append(f"⚠️ Пропускаю {func_name} - не могу прочитать index.py")
                continue
            
            index_data = index_resp.json()
            index_content = base64.b64decode(index_data['content']).decode('utf-8')
            
            # Читаем requirements.txt если есть
            requirements = ""
            req_url = f'https://api.github.com/repos/{github_repo}/contents/backend/{func_name}/requirements.txt'
            req_resp = requests.get(req_url, headers=headers_gh, timeout=10)
            
            if req_resp.status_code == 200:
                req_data = req_resp.json()
                requirements = base64.b64decode(req_data['content']).decode('utf-8')
            
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
                "description": f"Function {func_name} from poehali.dev"
            }
            
            # Сначала проверяем, существует ли функция
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
                    logs.append(f"  ✓ Функция {func_name} уже существует")
                    break
            
            # Если не существует - создаём
            if not function_id:
                create_func_resp = requests.post(
                    "https://serverless-functions.api.cloud.yandex.net/functions/v1/functions",
                    headers={**headers, "Content-Type": "application/json"},
                    json=function_payload,
                    timeout=30
                )
                
                if create_func_resp.status_code in [200, 201]:
                    resp_data = create_func_resp.json()
                    # Yandex Cloud возвращает operation, ждём её завершения
                    operation_id = resp_data.get('id')
                    if operation_id:
                        time.sleep(2)
                        # Получаем список функций снова
                        list_resp = requests.get(
                            f"https://serverless-functions.api.cloud.yandex.net/functions/v1/functions?folderId={folder_id}",
                            headers=headers,
                            timeout=10
                        )
                        functions = list_resp.json().get('functions', [])
                        for f in functions:
                            if f['name'] == func_name:
                                function_id = f['id']
                                break
                    logs.append(f"  ✓ Создана новая функция")
                else:
                    logs.append(f"❌ Ошибка создания {func_name}: {create_func_resp.text[:200]}")
                    continue
            
            if not function_id:
                logs.append(f"❌ Не удалось получить ID функции {func_name}")
                continue
            
            # Создаём версию функции с МАКСИМАЛЬНЫМ timeout
            version_payload = {
                "functionId": function_id,
                "runtime": "python311",
                "entrypoint": "index.handler",
                "resources": {"memory": "268435456"},
                "executionTimeout": "600s",
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
            
            # Получаем HTTP URL функции
            function_url = f"https://functions.yandexcloud.net/{function_id}"
            function_urls[func_name] = function_url
            
            logs.append(f"✅ {func_name} задеплоена: {function_url}")
            deployed_functions.append(func_name)
        
        logs.append("")
        logs.append(f"🎉 Готово! Задеплоено функций: {len(deployed_functions)}")
        
        # Обновляем func2url.json в GitHub если указан репозиторий
        if github_repo and github_token and function_urls:
            logs.append("")
            logs.append("🔄 Обновляю func2url.json в GitHub...")
            
            try:
                headers_gh = {
                    'Authorization': f'Bearer {github_token}',
                    'Accept': 'application/vnd.github.v3+json'
                }
                
                file_path = 'backend/func2url.json'
                url_gh = f'https://api.github.com/repos/{github_repo}/contents/{file_path}'
                
                # Читаем текущий файл
                get_resp = requests.get(url_gh, headers=headers_gh, timeout=10)
                
                current_func2url = {}
                file_sha = None
                
                if get_resp.status_code == 200:
                    file_data = get_resp.json()
                    file_sha = file_data['sha']
                    content = base64.b64decode(file_data['content']).decode('utf-8')
                    current_func2url = json.loads(content)
                
                # Обновляем URL
                updated_count = 0
                for func_name, new_url in function_urls.items():
                    if current_func2url.get(func_name) != new_url:
                        current_func2url[func_name] = new_url
                        updated_count += 1
                
                if updated_count > 0:
                    # Сохраняем
                    new_content = json.dumps(current_func2url, indent=2, ensure_ascii=False)
                    encoded_content = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')
                    
                    commit_data = {
                        'message': f'chore: update func2url.json with {updated_count} new URLs from Yandex Cloud',
                        'content': encoded_content,
                        'branch': 'main'
                    }
                    
                    if file_sha:
                        commit_data['sha'] = file_sha
                    
                    put_resp = requests.put(url_gh, headers=headers_gh, json=commit_data, timeout=15)
                    
                    if put_resp.status_code in [200, 201]:
                        logs.append(f"✅ func2url.json обновлён! Изменено URL: {updated_count}")
                    else:
                        logs.append(f"⚠️ Ошибка обновления GitHub: {put_resp.json().get('message', 'Unknown')}")
                else:
                    logs.append("✓ func2url.json не изменился")
                    
            except Exception as gh_error:
                logs.append(f"⚠️ Ошибка обновления GitHub: {str(gh_error)}")
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'success': True,
                'deployed': deployed_functions,
                'function_urls': function_urls,
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