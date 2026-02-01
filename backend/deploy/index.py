import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import paramiko
import requests
import time
from io import StringIO


def handler(event: dict, context) -> dict:
    """Деплой проекта на VM сервер: клонирование репо, билд фронтенда, настройка nginx, деплой функций"""
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
        deploy_type = body.get('type', 'all')
        
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
            SELECT dc.*, vm.ip_address, vm.name as vm_name, vm.ssh_private_key, vm.ssh_user
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
            logs.append("Создай VM и привяжи её к конфигу")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'VM не привязана', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        vm_ip = config['ip_address']
        ssh_key = config.get('ssh_private_key')
        ssh_user = config.get('ssh_user', 'ubuntu')
        domain = config['domain']
        github_repo = config['github_repo']
        
        if not ssh_key:
            logs.append("❌ SSH ключ не найден для VM")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'SSH ключ не настроен', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        logs.append(f"🖥️  Сервер: {vm_ip}")
        logs.append(f"👤 SSH: {ssh_user}@{vm_ip}")
        logs.append("")
        
        # Подключаемся к VM по SSH
        logs.append("🔌 Подключаюсь к серверу...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            pkey = paramiko.RSAKey.from_private_key(StringIO(ssh_key))
            ssh.connect(vm_ip, username=ssh_user, pkey=pkey, timeout=30)
            logs.append("✅ SSH подключение установлено")
        except Exception as e:
            logs.append(f"❌ Не могу подключиться по SSH: {str(e)}")
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'SSH connection failed', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        def run_cmd(cmd: str, ignore_errors=False):
            stdin, stdout, stderr = ssh.exec_command(cmd)
            exit_code = stdout.channel.recv_exit_status()
            output = stdout.read().decode('utf-8').strip()
            error = stderr.read().decode('utf-8').strip()
            
            if exit_code != 0 and not ignore_errors:
                raise Exception(f"Команда завершилась с ошибкой: {error or output}")
            
            return output, error, exit_code
        
        try:
            # 1. Клонируем репозиторий
            logs.append("📥 Клонирую репозиторий...")
            project_dir = f"/var/www/{domain}"
            
            run_cmd(f"sudo rm -rf {project_dir}", ignore_errors=True)
            run_cmd(f"sudo mkdir -p {project_dir}")
            run_cmd(f"sudo chown -R {ssh_user}:{ssh_user} {project_dir}")
            
            if github_token:
                clone_url = f"https://{github_token}@github.com/{github_repo}.git"
            else:
                clone_url = f"https://github.com/{github_repo}.git"
            
            output, _, _ = run_cmd(f"cd {project_dir} && git clone {clone_url} .")
            logs.append("✅ Репозиторий склонирован")
            
            # 2. Устанавливаем зависимости и билдим фронтенд
            logs.append("📦 Устанавливаю зависимости...")
            run_cmd(f"cd {project_dir} && npm install")
            logs.append("✅ Зависимости установлены")
            
            logs.append("🏗️  Собираю фронтенд...")
            run_cmd(f"cd {project_dir} && npm run build")
            logs.append("✅ Фронтенд собран")
            
            # 3. Настраиваем nginx
            logs.append("⚙️  Настраиваю nginx...")
            nginx_config = f"""server {{
    listen 80;
    server_name {domain};
    root {project_dir}/dist;
    index index.html;
    
    location / {{
        try_files $uri $uri/ /index.html;
    }}
    
    location ~ /\\.git {{
        deny all;
    }}
}}"""
            
            run_cmd(f"sudo tee /etc/nginx/sites-available/{domain} > /dev/null", ignore_errors=True)
            ssh.exec_command(f"sudo tee /etc/nginx/sites-available/{domain} << 'EOF'\n{nginx_config}\nEOF")
            time.sleep(1)
            
            run_cmd(f"sudo ln -sf /etc/nginx/sites-available/{domain} /etc/nginx/sites-enabled/{domain}", ignore_errors=True)
            
            # Проверяем конфиг nginx
            _, error, exit_code = run_cmd("sudo nginx -t", ignore_errors=True)
            if exit_code != 0:
                logs.append(f"⚠️ Nginx конфиг: {error}")
            else:
                logs.append("✅ Nginx конфиг валиден")
            
            run_cmd("sudo systemctl reload nginx")
            logs.append("✅ Nginx перезагружен")
            
            # 4. Деплой backend функций ОТКЛЮЧЕН (слишком долго для одной функции)
            # Используй отдельную функцию deploy-functions для этого
            if False and deploy_type == 'all':
                logs.append("")
                logs.append("☁️ Деплою backend функции в Yandex Cloud...")
                
                try:
                    oauth_token = os.environ.get('YANDEX_CLOUD_TOKEN')
                    
                    # Получаем IAM токен
                    iam_resp = requests.post(
                        "https://iam.api.cloud.yandex.net/iam/v1/tokens",
                        json={"yandexPassportOauthToken": oauth_token},
                        timeout=10
                    )
                    iam_token = iam_resp.json()["iamToken"]
                    
                    # Получаем folder_id
                    headers_yc = {"Authorization": f"Bearer {iam_token}"}
                    clouds_resp = requests.get(
                        "https://resource-manager.api.cloud.yandex.net/resource-manager/v1/clouds",
                        headers=headers_yc,
                        timeout=10
                    )
                    cloud_id = clouds_resp.json()["clouds"][0]["id"]
                    
                    folders_resp = requests.get(
                        f"https://resource-manager.api.cloud.yandex.net/resource-manager/v1/folders?cloudId={cloud_id}",
                        headers=headers_yc,
                        timeout=10
                    )
                    folder_id = folders_resp.json()["folders"][0]["id"]
                    
                    # Читаем функции из GitHub
                    headers_gh = {
                        'Authorization': f'token {github_token}',
                        'Accept': 'application/vnd.github.v3+json'
                    }
                    
                    repo_url = f'https://api.github.com/repos/{github_repo}'
                    repo_resp = requests.get(repo_url, headers=headers_gh, timeout=10)
                    
                    if repo_resp.status_code != 200:
                        logs.append(f"⚠️ Репозиторий недоступен для функций")
                    else:
                        repo_data = repo_resp.json()
                        default_branch = repo_data.get('default_branch', 'main')
                        
                        backend_url = f'https://api.github.com/repos/{github_repo}/contents/backend?ref={default_branch}'
                        backend_resp = requests.get(backend_url, headers=headers_gh, timeout=10)
                        
                        if backend_resp.status_code == 200:
                            backend_items = backend_resp.json()
                            function_dirs = []
                            
                            for item in backend_items:
                                if item['type'] == 'dir' and item['name'] != 'func2url.json':
                                    index_url = f"https://api.github.com/repos/{github_repo}/contents/backend/{item['name']}/index.py"
                                    index_check = requests.get(index_url, headers=headers_gh, timeout=5)
                                    if index_check.status_code == 200:
                                        function_dirs.append(item['name'])
                            
                            logs.append(f"  Найдено функций: {len(function_dirs)}")
                            
                            # Деплоим каждую функцию (упрощённая версия)
                            deployed_count = 0
                            for func_name in function_dirs[:5]:
                                try:
                                    index_url = f'https://api.github.com/repos/{github_repo}/contents/backend/{func_name}/index.py'
                                    index_resp = requests.get(index_url, headers=headers_gh, timeout=10)
                                    
                                    if index_resp.status_code == 200:
                                        import base64
                                        import zipfile
                                        from io import BytesIO
                                        
                                        index_data = index_resp.json()
                                        index_content = base64.b64decode(index_data['content']).decode('utf-8')
                                        
                                        # Читаем requirements.txt
                                        requirements = ""
                                        req_url = f'https://api.github.com/repos/{github_repo}/contents/backend/{func_name}/requirements.txt'
                                        req_resp = requests.get(req_url, headers=headers_gh, timeout=10)
                                        
                                        if req_resp.status_code == 200:
                                            req_data = req_resp.json()
                                            requirements = base64.b64decode(req_data['content']).decode('utf-8')
                                        
                                        # Создаём zip
                                        zip_buffer = BytesIO()
                                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                                            zip_file.writestr('index.py', index_content)
                                            if requirements:
                                                zip_file.writestr('requirements.txt', requirements)
                                        
                                        zip_content = zip_buffer.getvalue()
                                        
                                        # Проверяем существует ли функция
                                        list_resp = requests.get(
                                            f"https://serverless-functions.api.cloud.yandex.net/functions/v1/functions?folderId={folder_id}",
                                            headers=headers_yc,
                                            timeout=10
                                        )
                                        existing_functions = {f['name']: f['id'] for f in list_resp.json().get('functions', [])}
                                        function_id = existing_functions.get(func_name)
                                        
                                        if not function_id:
                                            # Создаём функцию
                                            create_payload = {
                                                "folderId": folder_id,
                                                "name": func_name,
                                                "description": f"Function {func_name}"
                                            }
                                            
                                            create_resp = requests.post(
                                                "https://serverless-functions.api.cloud.yandex.net/functions/v1/functions",
                                                headers={**headers_yc, "Content-Type": "application/json"},
                                                json=create_payload,
                                                timeout=30
                                            )
                                            
                                            if create_resp.status_code in [200, 201]:
                                                time.sleep(2)
                                                list_resp2 = requests.get(
                                                    f"https://serverless-functions.api.cloud.yandex.net/functions/v1/functions?folderId={folder_id}",
                                                    headers=headers_yc,
                                                    timeout=10
                                                )
                                                existing_functions2 = {f['name']: f['id'] for f in list_resp2.json().get('functions', [])}
                                                function_id = existing_functions2.get(func_name)
                                        
                                        if function_id:
                                            # Создаём версию функции
                                            version_payload = {
                                                "functionId": function_id,
                                                "runtime": "python311",
                                                "entrypoint": "index.handler",
                                                "resources": {"memory": 134217728},
                                                "executionTimeout": "30s",
                                                "serviceAccountId": None,
                                                "package": {"content": base64.b64encode(zip_content).decode('utf-8')}
                                            }
                                            
                                            version_resp = requests.post(
                                                f"https://serverless-functions.api.cloud.yandex.net/functions/v1/versions",
                                                headers={**headers_yc, "Content-Type": "application/json"},
                                                json=version_payload,
                                                timeout=60
                                            )
                                            
                                            if version_resp.status_code in [200, 201]:
                                                # Делаем функцию публичной
                                                requests.post(
                                                    f"https://serverless-functions.api.cloud.yandex.net/functions/v1/functions/{function_id}:setAccessBindings",
                                                    headers={**headers_yc, "Content-Type": "application/json"},
                                                    json={"accessBindings": [{"roleId": "functions.functionInvoker", "subject": {"id": "allUsers", "type": "system"}}]},
                                                    timeout=10
                                                )
                                                
                                                deployed_count += 1
                                
                                except Exception as e:
                                    logs.append(f"  ⚠️ {func_name}: {str(e)[:50]}")
                            
                            if deployed_count > 0:
                                logs.append(f"✅ Задеплоено функций: {deployed_count}")
                        else:
                            logs.append("⚠️ Папка /backend не найдена в репо")
                
                except Exception as e:
                    logs.append(f"⚠️ Деплой функций: {str(e)[:100]}")
            
            logs.append("")
            logs.append(f"🎉 Фронтенд задеплоен!")
            logs.append(f"🌐 Сайт доступен: http://{domain}")
            logs.append(f"   (или http://{vm_ip} если DNS не настроен)")
            logs.append("")
            logs.append("💡 Для деплоя backend функций используй отдельную кнопку")
            
            ssh.close()
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'success': True,
                    'logs': logs,
                    'url': f"http://{domain}",
                    'ip_url': f"http://{vm_ip}"
                }, default=str),
                'isBase64Encoded': False
            }
        
        except Exception as e:
            logs.append(f"❌ Ошибка деплоя: {str(e)}")
            ssh.close()
            
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