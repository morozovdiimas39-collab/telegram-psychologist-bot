#!/usr/bin/env python3
"""
Простой скрипт для создания VM в Yandex Cloud.
Запускается ЛОКАЛЬНО на твоём компьютере.

Использование:
  python3 yc-create-vm.py
"""

import requests
import time
import json

OAUTH_TOKEN = "y0__xCtvb3CARjB3RMg3fH9zxXjpBff6RKbq5G1BPxGOJWLWfyL1Q"

print("🚀 Создание VM в Yandex Cloud\n")

# Шаг 1: IAM токен
print("1️⃣ Получаю IAM токен...")
iam_resp = requests.post(
    "https://iam.api.cloud.yandex.net/iam/v1/tokens",
    json={"yandexPassportOauthToken": OAUTH_TOKEN}
)
iam_resp.raise_for_status()
iam_token = iam_resp.json()["iamToken"]
print("✅ IAM токен получен\n")

headers = {"Authorization": f"Bearer {iam_token}"}

# Шаг 2: Folder ID
print("2️⃣ Получаю folder ID...")
folders_resp = requests.get(
    "https://resource-manager.api.cloud.yandex.net/resource-manager/v1/folders",
    headers=headers
)
folders_resp.raise_for_status()
folders = folders_resp.json()["folders"]
folder_id = folders[0]["id"]
print(f"✅ Folder ID: {folder_id}\n")

# Шаг 3: Проверка существующих VM
print("3️⃣ Проверяю существующие VM...")
instances_resp = requests.get(
    f"https://compute.api.cloud.yandex.net/compute/v1/instances?folderId={folder_id}",
    headers=headers
)
instances = instances_resp.json().get("instances", [])

for vm in instances:
    if vm.get("name") == "deploy-server":
        print(f"✅ VM уже существует!")
        vm_ip = None
        for iface in vm.get("networkInterfaces", []):
            nat = iface.get("primaryV4Address", {}).get("oneToOneNat", {})
            vm_ip = nat.get("address")
            if vm_ip:
                break
        
        print(f"\n{'='*60}")
        print(f"📋 IP адрес: {vm_ip}")
        print(f"📋 Webhook URL: http://{vm_ip}:9000/deploy")
        print(f"\n💡 Добавь эти секреты в poehali.dev:")
        print(f"   VM_IP_ADDRESS = {vm_ip}")
        print(f"   VM_WEBHOOK_URL = http://{vm_ip}:9000/deploy")
        print(f"{'='*60}")
        exit(0)

print("⚠️ VM не найдена, создаю новую...\n")

# Шаг 4: Получение subnet
print("4️⃣ Получаю subnet...")
subnets_resp = requests.get(
    f"https://vpc.api.cloud.yandex.net/vpc/v1/subnets?folderId={folder_id}",
    headers=headers
)
subnets = subnets_resp.json().get("subnets", [])

if not subnets:
    print("❌ Нет подсетей! Создай сеть в Yandex Cloud вручную.")
    exit(1)

subnet_id = subnets[0]["id"]
print(f"✅ Subnet ID: {subnet_id}\n")

# Шаг 5: Cloud-init скрипт
cloud_init = """#cloud-config
package_update: true
packages:
  - docker.io
  - docker-compose
  - nginx
  - postgresql
  - certbot
  - python3-certbot-nginx
  - python3-pip
  - git

runcmd:
  - systemctl enable docker && systemctl start docker
  - systemctl enable nginx && systemctl start nginx  
  - systemctl enable postgresql && systemctl start postgresql
  - sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
  - pip3 install flask requests
  - echo 'VM готова!' > /tmp/ready
"""

# Шаг 6: Создание VM
print("5️⃣ Создаю VM (это займёт 2-3 минуты)...")

vm_payload = {
    "folderId": folder_id,
    "name": "deploy-server",
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
    json=vm_payload
)

if create_resp.status_code != 200:
    print(f"❌ Ошибка: {create_resp.text}")
    exit(1)

operation_id = create_resp.json()["id"]
print(f"✅ Операция запущена: {operation_id}")
print("⏳ Жду завершения...\n")

# Ждём завершения
for i in range(60):
    time.sleep(5)
    op_resp = requests.get(
        f"https://operation.api.cloud.yandex.net/operations/{operation_id}",
        headers=headers
    )
    op_data = op_resp.json()
    
    if op_data.get("done"):
        if op_data.get("error"):
            print(f"❌ Ошибка: {op_data['error']}")
            exit(1)
        
        vm_id = op_data["response"]["id"]
        print(f"✅ VM создана: {vm_id}\n")
        
        # Получаем IP
        vm_resp = requests.get(
            f"https://compute.api.cloud.yandex.net/compute/v1/instances/{vm_id}",
            headers=headers
        )
        vm_info = vm_resp.json()
        
        vm_ip = None
        for iface in vm_info.get("networkInterfaces", []):
            nat = iface.get("primaryV4Address", {}).get("oneToOneNat", {})
            vm_ip = nat.get("address")
            if vm_ip:
                break
        
        print(f"\n{'='*60}")
        print(f"✅ ВСЁ ГОТОВО!")
        print(f"{'='*60}")
        print(f"📋 IP адрес: {vm_ip}")
        print(f"📋 Webhook URL: http://{vm_ip}:9000/deploy")
        print(f"\n💡 Добавь эти секреты в poehali.dev:")
        print(f"   VM_IP_ADDRESS = {vm_ip}")
        print(f"   VM_WEBHOOK_URL = http://{vm_ip}:9000/deploy")
        print(f"\n⏳ VM будет готова через 3-5 минут (установка пакетов)")
        print(f"{'='*60}")
        exit(0)
    
    print(f"⏳ {i*5} секунд...")

print("❌ Таймаут")
exit(1)
