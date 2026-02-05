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
            logs.append("💡 Эта VM была создана без автоматического SSH")
            logs.append("   Создай новую VM через кнопку 'Создать VM'")
            logs.append("   И выбери её в настройках конфига")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'SSH ключ не настроен (VM устарела)', 'logs': logs}),
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
            logs.append(f"❌ SSH не работает: {str(e)[:100]}")
            logs.append("")
            logs.append("🔧 Создаю новую VM с правильными SSH ключами...")
            
            # Автоматически создаём новую VM
            try:
                from cryptography.hazmat.primitives import serialization
                from cryptography.hazmat.primitives.asymmetric import rsa
                from cryptography.hazmat.backends import default_backend
                
                oauth_token = os.environ.get('YANDEX_CLOUD_TOKEN')
                
                # Получаем IAM токен
                iam_resp = requests.post(
                    "https://iam.api.cloud.yandex.net/iam/v1/tokens",
                    json={"yandexPassportOauthToken": oauth_token},
                    timeout=10
                )
                iam_token = iam_resp.json()["iamToken"]
                headers_yc = {"Authorization": f"Bearer {iam_token}"}
                
                # Получаем folder_id
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
                
                # Генерируем SSH ключи
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                    backend=default_backend()
                )
                
                private_pem = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption()
                ).decode('utf-8')
                
                public_key = private_key.public_key()
                public_openssh = public_key.public_bytes(
                    encoding=serialization.Encoding.OpenSSH,
                    format=serialization.PublicFormat.OpenSSH
                ).decode('utf-8')
                
                # Получаем subnet
                subnets_resp = requests.get(
                    f"https://vpc.api.cloud.yandex.net/vpc/v1/subnets?folderId={folder_id}",
                    headers=headers_yc,
                    timeout=10
                )
                subnets = subnets_resp.json().get("subnets", [])
                subnet_id = None
                for subnet in subnets:
                    if subnet.get("zoneId") == "ru-central1-a":
                        subnet_id = subnet["id"]
                        break
                
                if not subnet_id:
                    raise Exception("Subnet not found")
                
                # Cloud-init с публичным ключом
                cloud_init = f"""#cloud-config
package_update: true
packages:
  - nginx
  - git
  - nodejs
  - npm

users:
  - name: ubuntu
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys:
      - {public_openssh}

runcmd:
  - systemctl enable nginx && systemctl start nginx
  - mkdir -p /var/www
  - chown -R ubuntu:ubuntu /var/www
"""
                
                new_vm_name = f"{domain.replace('.', '-')}-vm"
                
                # Создаём VM
                vm_payload = {
                    "folderId": folder_id,
                    "name": new_vm_name,
                    "zoneId": "ru-central1-a",
                    "platformId": "standard-v3",
                    "resourcesSpec": {"memory": "4294967296", "cores": "2"},
                    "bootDiskSpec": {
                        "mode": "READ_WRITE",
                        "autoDelete": True,
                        "diskSpec": {
                            "size": "32212254720",
                            "typeId": "network-ssd",
                            "imageId": "fd8kdq6d0p8sij7h5qe3"
                        }
                    },
                    "networkInterfaceSpecs": [{
                        "subnetId": subnet_id,
                        "primaryV4AddressSpec": {"oneToOneNatSpec": {"ipVersion": "IPV4"}}
                    }],
                    "metadata": {"user-data": cloud_init}
                }
                
                create_resp = requests.post(
                    "https://compute.api.cloud.yandex.net/compute/v1/instances",
                    headers={**headers_yc, "Content-Type": "application/json"},
                    json=vm_payload,
                    timeout=30
                )
                
                if create_resp.status_code == 200:
                    operation_data = create_resp.json()
                    vm_id_from_operation = operation_data.get("metadata", {}).get("instanceId")
                    
                    # Сохраняем в БД
                    cur.execute(
                        f"""
                        INSERT INTO {schema}.vm_instances 
                        (name, ip_address, ssh_user, status, yandex_vm_id, ssh_private_key)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (new_vm_name, None, "ubuntu", "creating", vm_id_from_operation, private_pem)
                    )
                    new_vm_db_id = cur.fetchone()["id"]
                    
                    # Обновляем конфиг на новую VM
                    cur.execute(
                        f"UPDATE {schema}.deploy_configs SET vm_instance_id = %s WHERE name = %s",
                        (new_vm_db_id, config_name)
                    )
                    conn.commit()
                    
                    logs.append(f"✅ Новая VM '{new_vm_name}' создаётся!")
                    logs.append("⏳ Подожди 2-3 минуты и попробуй деплой снова")
                    logs.append(f"   Конфиг автоматически привязан к новой VM")
                    
                    return {
                        'statusCode': 202,
                        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                        'body': json.dumps({'message': 'VM создаётся', 'logs': logs, 'new_vm_id': new_vm_db_id}),
                        'isBase64Encoded': False
                    }
                else:
                    raise Exception(f"VM creation failed: {create_resp.text[:200]}")
                    
            except Exception as vm_error:
                logs.append(f"❌ Не удалось создать VM: {str(vm_error)[:150]}")
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'SSH failed and auto-create VM failed', 'logs': logs}),
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
            # 0. Проверяем и устанавливаем git, nodejs, npm если нужно
            logs.append("🔧 Проверяю установку необходимых пакетов...")
            
            # Проверяем git
            _, _, git_check = run_cmd("which git", ignore_errors=True)
            if git_check != 0:
                logs.append("  📦 Устанавливаю git...")
                run_cmd("sudo apt-get update && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y git")
                logs.append("  ✅ git установлен")
            
            # Проверяем nodejs
            _, _, node_check = run_cmd("which node", ignore_errors=True)
            if node_check != 0:
                logs.append("  📦 Устанавливаю nodejs и npm...")
                run_cmd("sudo apt-get update && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nodejs npm")
                logs.append("  ✅ nodejs установлен")
            
            # Проверяем nginx
            _, _, nginx_check = run_cmd("which nginx", ignore_errors=True)
            if nginx_check != 0:
                logs.append("  📦 Устанавливаю nginx...")
                run_cmd("sudo apt-get update && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nginx")
                run_cmd("sudo systemctl enable nginx && sudo systemctl start nginx")
                logs.append("  ✅ nginx установлен")
            
            logs.append("✅ Все пакеты готовы")
            logs.append("")
            
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