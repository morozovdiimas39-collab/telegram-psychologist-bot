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
        
        # Читаем функции из локальной папки backend
        logs.append("📦 Читаю функции из проекта...")
        backend_path = Path(__file__).parent.parent
        
        function_dirs = [d.name for d in backend_path.iterdir() if d.is_dir() and (d / 'index.py').exists()]
        logs.append(f"✅ Найдено функций: {len(function_dirs)}")
        
        deployed_functions = []
        function_urls = {}
        
        # Деплоим каждую функцию
        for func_name in function_dirs:
            logs.append(f"🚀 Деплою функцию: {func_name}")
            
            func_path = backend_path / func_name
            
            # Читаем index.py
            index_file = func_path / 'index.py'
            if not index_file.exists():
                logs.append(f"⚠️ Пропускаю {func_name} - нет index.py")
                continue
            
            with open(index_file, 'r', encoding='utf-8') as f:
                index_content = f.read()
            
            # Читаем requirements.txt если есть
            requirements = ""
            req_file = func_path / 'requirements.txt'
            if req_file.exists():
                with open(req_file, 'r', encoding='utf-8') as f:
                    requirements = f.read()
            
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
            
            # Получаем HTTP URL функции
            function_url = f"https://functions.yandexcloud.net/{function_id}"
            function_urls[func_name] = function_url
            
            logs.append(f"✅ {func_name} задеплоена: {function_url}")
            deployed_functions.append(func_name)
        
        logs.append("")
        logs.append(f"🎉 Готово! Задеплоено функций: {len(deployed_functions)}")
        
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