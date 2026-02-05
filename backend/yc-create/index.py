import json
import os
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
import base64
import secrets
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


def handler(event: dict, context) -> dict:
    """Создать VM в Yandex Cloud автоматически"""
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

    oauth_token = os.environ.get('YANDEX_CLOUD_TOKEN')
    
    try:
        # Парсим имя VM из запроса или генерируем уникальное
        body = json.loads(event.get('body', '{}'))
        vm_name = body.get('name', f'deploy-vm-{context.request_id[:8]}')
        
        logs = [f"🔐 Создаём VM: {vm_name}"]
        
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
        
        logs.append("☁️ Получаю cloud ID...")
        clouds_resp = requests.get(
            "https://resource-manager.api.cloud.yandex.net/resource-manager/v1/clouds",
            headers=headers,
            timeout=10
        )
        
        if clouds_resp.status_code != 200:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'Clouds API error: {clouds_resp.text}', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        clouds = clouds_resp.json().get("clouds", [])
        if not clouds:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'No clouds found in account', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        cloud_id = clouds[0]["id"]
        logs.append(f"✅ Cloud ID: {cloud_id}")
        
        logs.append("📁 Получаю folder ID...")
        folders_resp = requests.get(
            f"https://resource-manager.api.cloud.yandex.net/resource-manager/v1/folders?cloudId={cloud_id}",
            headers=headers,
            timeout=10
        )
        
        if folders_resp.status_code != 200:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'Folders API error: {folders_resp.text}', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        folders = folders_resp.json().get("folders", [])
        if not folders:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'No folders found in cloud', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        folder_id = folders[0]["id"]
        logs.append(f"✅ Folder ID: {folder_id}")
        
        logs.append("🔍 Проверяю VM...")
        instances_resp = requests.get(
            f"https://compute.api.cloud.yandex.net/compute/v1/instances?folderId={folder_id}",
            headers=headers,
            timeout=10
        )
        instances = instances_resp.json().get("instances", [])
        
        dsn = os.environ['DATABASE_URL']
        schema = os.environ.get('MAIN_DB_SCHEMA', 'public')
        
        for vm in instances:
            if vm.get("name") == vm_name:
                logs.append("✅ VM уже существует в Yandex Cloud")
                vm_ip = None
                for iface in vm.get("networkInterfaces", []):
                    nat = iface.get("primaryV4Address", {}).get("oneToOneNat", {})
                    vm_ip = nat.get("address")
                    if vm_ip:
                        break
                
                # Проверяем есть ли в БД
                conn = psycopg2.connect(dsn)
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute(
                    f"SELECT id FROM {schema}.vm_instances WHERE yandex_vm_id = %s",
                    (vm["id"],)
                )
                existing = cur.fetchone()
                
                if not existing:
                    logs.append("💾 Добавляю VM в БД...")
                    cur.execute(
                        f"""
                        INSERT INTO {schema}.vm_instances 
                        (name, ip_address, ssh_user, status, yandex_vm_id)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (vm_name, vm_ip, "ubuntu", "ready", vm["id"])
                    )
                    conn.commit()
                    logs.append("✅ VM сохранена в БД")
                
                cur.close()
                conn.close()
                
                webhook_url = f"http://{vm_ip}:9000/deploy"
                
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({
                        'success': True,
                        'ip': vm_ip,
                        'webhook': webhook_url,
                        'logs': logs
                    }),
                    'isBase64Encoded': False
                }
        
        logs.append("⚠️ VM не найдена, создаю...")
        
        # Генерируем SSH ключи
        logs.append("🔐 Генерирую SSH ключи...")
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
        
        logs.append(f"✅ SSH ключи сгенерированы")
        
        zone = "ru-central1-a"
        
        logs.append(f"📡 Получаю subnet в зоне {zone}...")
        subnets_resp = requests.get(
            f"https://vpc.api.cloud.yandex.net/vpc/v1/subnets?folderId={folder_id}",
            headers=headers,
            timeout=10
        )
        subnets = subnets_resp.json().get("subnets", [])
        
        subnet_id = None
        for subnet in subnets:
            if subnet.get("zoneId") == zone:
                subnet_id = subnet["id"]
                break
        
        if not subnet_id:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'No subnet found in zone {zone}', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        logs.append(f"✅ Subnet: {subnet_id}")
        
        # Подставляем публичный ключ в cloud-init
        cloud_init = f"""#cloud-config
package_update: true
packages:
  - docker.io
  - nginx
  - postgresql
  - postgresql-contrib
  - python3-pip
  - python3-flask
  - git
  - nodejs
  - npm

users:
  - name: ubuntu
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys:
      - {public_openssh}

write_files:
  - path: /usr/local/bin/deploy_server.py
    permissions: '0755'
    content: |
      #!/usr/bin/env python3
      from flask import Flask, request, jsonify
      import subprocess
      import os
      
      app = Flask(__name__)
      
      @app.route('/deploy', methods=['POST'])
      def deploy():
          data = request.get_json() or {{}}
          domain = data.get('domain', 'example.com')
          repo = data.get('repo', '')
          github_token = data.get('github_token', '')
          
          if not repo:
              return jsonify({{'error': 'repo required'}}), 400
          
          project_dir = f"/var/www/{{domain}}"
          
          try:
              # Удаляем старую версию
              subprocess.run(['sudo', 'rm', '-rf', project_dir], check=False)
              subprocess.run(['sudo', 'mkdir', '-p', project_dir], check=True)
              subprocess.run(['sudo', 'chown', '-R', 'ubuntu:ubuntu', project_dir], check=True)
              
              # Клонируем репо
              if github_token:
                  clone_url = f"https://{{github_token}}@github.com/{{repo}}.git"
              else:
                  clone_url = f"https://github.com/{{repo}}.git"
              
              subprocess.run(['git', 'clone', clone_url, project_dir], check=True, cwd='/tmp')
              
              # npm install и build
              subprocess.run(['npm', 'install'], check=True, cwd=project_dir)
              subprocess.run(['npm', 'run', 'build'], check=True, cwd=project_dir)
              
              # Настраиваем nginx
              nginx_config = f"""server {{{{
  listen 80;
  server_name {{domain}};
  root {{project_dir}}/dist;
  index index.html;
  
  location / {{{{
      try_files $uri $uri/ /index.html;
  }}}}
  
  location ~ /\\.git {{{{
      deny all;
  }}}}
}}}}"""
              
              with open(f'/etc/nginx/sites-available/{{domain}}', 'w') as f:
                  f.write(nginx_config)
              
              subprocess.run(['sudo', 'ln', '-sf', f'/etc/nginx/sites-available/{{domain}}', f'/etc/nginx/sites-enabled/{{domain}}'], check=False)
              subprocess.run(['sudo', 'nginx', '-t'], check=True)
              subprocess.run(['sudo', 'systemctl', 'reload', 'nginx'], check=True)
              
              return jsonify({{'success': True, 'message': f'Deployed {{domain}}'}}), 200
              
          except subprocess.CalledProcessError as e:
              return jsonify({{'error': str(e)}}), 500
          except Exception as e:
              return jsonify({{'error': str(e)}}), 500
      
      if __name__ == '__main__':
          app.run(host='0.0.0.0', port=9000)
  
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
  - systemctl enable nginx && systemctl start nginx
  - mkdir -p /var/www
  - chown -R ubuntu:ubuntu /var/www
  - pip3 install flask requests
  - systemctl daemon-reload
  - systemctl enable deploy-webhook && systemctl start deploy-webhook
  - echo 'VM готова' > /var/log/deploy_init.log
"""
        
        logs.append("🚀 Создаю VM...")
        
        vm_payload = {
            "folderId": folder_id,
            "name": vm_name,
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
            headers={**headers, "Content-Type": "application/json"},
            json=vm_payload,
            timeout=30
        )
        
        if create_resp.status_code != 200:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'Create failed: {create_resp.text[:300]}', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        operation_data = create_resp.json()
        operation_id = operation_data["id"]
        
        logs.append(f"✅ Операция запущена: {operation_id}")
        logs.append("💾 Сохраняю VM и SSH ключи в БД...")
        
        # Сохраняем VM в БД сразу со статусом creating
        conn = psycopg2.connect(dsn)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Сохраняем в БД с реальным ID VM из operation metadata
        vm_id_from_operation = operation_data.get("metadata", {}).get("instanceId", operation_id)
        
        # Используем ON CONFLICT для обработки дубликатов имён
        cur.execute(
            f"""
            INSERT INTO {schema}.vm_instances 
            (name, ip_address, ssh_user, status, yandex_vm_id, ssh_private_key)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE 
            SET status = 'creating', 
                yandex_vm_id = EXCLUDED.yandex_vm_id,
                ssh_private_key = EXCLUDED.ssh_private_key,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
            """,
            (vm_name, None, "ubuntu", "creating", vm_id_from_operation, private_pem)
        )
        vm_db_id = cur.fetchone()["id"]
        conn.commit()
        cur.close()
        conn.close()
        
        logs.append(f"✅ VM #{vm_db_id} сохранена с SSH ключом")
        logs.append("⏳ VM создаётся 2-3 минуты, обнови список")
        
        return {
            'statusCode': 202,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'success': True, 'operation_id': operation_id, 'vm_id': vm_db_id, 'logs': logs}),
            'isBase64Encoded': False
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)}),
            'isBase64Encoded': False
        }