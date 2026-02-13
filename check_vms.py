#!/usr/bin/env python3
"""
Скрипт для проверки списка созданных VM в Yandex Cloud
"""

import requests
import jwt
import time
import os

# Переменные окружения (замени на свои)
SERVICE_ACCOUNT_ID = "ajea2l0hjh86sa9a3g08"
SERVICE_ACCOUNT_KEY_ID = "ajeke7hvv73d03siopbo"
SERVICE_ACCOUNT_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCkbLt7NgifSTJk
oCoW76w491GeTvikuaDdWx0AZ9zLug8CW0M1XI/NGIRT6JnEOFWBBt+a6+av8kAR
qEREBphM/vB3zjIDUjtI+mXqQkAbd0GRo7fi6fyXLA7v2jVL8Lzu2hQio4rKsyJk
xrW9DlYINX3CGC3kZyKnskvud6D386XFMVNIeWrKa0l50daR3bkRHnNoEPJaC5yB
LcBcTac+hbjPWjlxqtg03N2smwZErAHMiu3eOSk4pJcrydBm7o+A9qdCMMsjL3Bk
9maaXMyXJxgE7xGcMiAR1e/OvDOvnug9u4zDhuzM9sQvf15R4EUgOEFQb05ObjNq
v4zMgoTPAgMBAAECggEADJy2iM3tPWKc9fD/KYE64ae+3/jIw8HlX/VUNSrCWfIs
oo6jih1Ofnnp9JG78bwsetgvILAFoutfFLumeN1Uo1tO0LHFTlHpcECcvqpURocQ
RX6cZVBzapkbkDRZsDiIFX4u2zVWORQiiD5hxF2sJbcMrW2zX3i1xM09W85bT4mG
XIn8qAisIkYoDMHzOLoD2/KvX1ya9dLQlVzcLI5cql7jnmiym7DF0J6uDFiW+cFt
5cA2EUpNaoaFwKmFb00PhjOd6tbb2rKH3mCnMrxtCjR9WrqJpQ3G+WsR06wAQN3r
vZvxf8TLD1tb/9WyAN3dGWEm8vOvWoDHSfVYd+gMmQKBgQDAazFDpYdlUVEeFJKu
Gc0+eowV3IDNd2/NtyVOEr8Kxv5l0C+s6WOZl/LAmqRxx9fRMxJ81oBYvT+pdJ7C
aoV2gCJCM9fXHD83eoyJBYJ3VhL+fnFqdSfHshTBokPGNxkE9yujd0XNYsvej2gs
nGSn+SCrjBXt4mVb+BX24vrvRQKBgQDawYNV9n8gQyhpejpSPnTFcyaxkazZcYQB
TDnD8yk1TnRueycIxQMu22za3ciUEAhNxTWjHWWrNrMVlJN/M4l+r+cUAtmN8fAK
bQJ1Xnvt8jg6XGGgCzbAGSuZ5KzIRty8I2OZ3pkUNB1iOpzUYryLhTBRXpGVEaLM
aRtuot7LAwKBgGCOqecPTpVKLBGTM1QIgJUku91QjJYOpF0v1ZmLELEg0JJY2UPE
zoVJ2bhLIdAy/5rsLQ/WOAvP0/1+FxjqiVTA0fA0wdAhTZvSdGliCWlHGTr6SoGo
jrDILWBJxAbYqUZznkNmW/HH7RQfFKCmTmB4RKuxHWQFYuW25ZbBqjidAoGBAIPZ
sVyFxxfeAqSYnEBoDp/YCRFr+V/SULsrg4G8tTDBCeJxbhSWEpYSgWjl1niPtUGS
xQJ8vIPW41f1hnVbzdrDESd5lEE++ux9ycaOXWoM3aEnf1wkhiqAwUvvjcjlFTR8
rBLZHTEVPESxiUdl/7ikXXwd4OeViqdkDrm/h0ObAoGANJ2dNZKdD/WNTYwiC3aN
7+MYYKV8/YI696qlEhxk0zYH5Gog2l6yGZWbL3eii2IQRoJd6bgY4O/zAPzfE+Qa
y5pwu/aIOUIiaU8bTDGqlXWidawDasvDF/gUWEfyuyEspjrmmuon4neCWHFZrp1p
Cz2MaMksxHJfvfC9x/QC4J0=
-----END PRIVATE KEY-----"""
FOLDER_ID = "b1gga4kkbv0csaelq94p"

print("🔍 Проверка списка VM в Yandex Cloud...\n")

# Создаём JWT токен
now = int(time.time())
payload = {
    'aud': 'https://iam.api.cloud.yandex.net/iam/v1/tokens',
    'iss': SERVICE_ACCOUNT_ID,
    'iat': now,
    'exp': now + 3600
}

headers_jwt = {'kid': SERVICE_ACCOUNT_KEY_ID}
jwt_token = jwt.encode(payload, SERVICE_ACCOUNT_PRIVATE_KEY, algorithm='PS256', headers=headers_jwt)

# Получаем IAM токен
print("1️⃣ Получаю IAM токен...")
iam_resp = requests.post(
    'https://iam.api.cloud.yandex.net/iam/v1/tokens',
    json={'jwt': jwt_token},
    timeout=10
)

if iam_resp.status_code != 200:
    print(f"❌ Ошибка получения IAM токена: {iam_resp.status_code} - {iam_resp.text}")
    exit(1)

iam_token = iam_resp.json()['iamToken']
print("✅ IAM токен получен\n")

# Получаем список VM
headers = {'Authorization': f'Bearer {iam_token}'}
print(f"2️⃣ Получаю список VM из folder {FOLDER_ID}...")
instances_resp = requests.get(
    f'https://compute.api.cloud.yandex.net/compute/v1/instances?folderId={FOLDER_ID}',
    headers=headers,
    timeout=10
)

if instances_resp.status_code != 200:
    print(f"❌ Ошибка получения списка VM: {instances_resp.status_code} - {instances_resp.text}")
    exit(1)

instances = instances_resp.json().get('instances', [])
print(f"✅ Найдено VM: {len(instances)}\n")

if not instances:
    print("⚠️ VM не найдены")
else:
    print("📋 Список VM:\n")
    for vm in instances:
        vm_id = vm.get('id', 'N/A')
        vm_name = vm.get('name', 'N/A')
        status = vm.get('status', 'N/A')
        
        # Получаем IP адрес
        interfaces = vm.get('networkInterfaces', [])
        ip_address = 'N/A'
        if interfaces:
            nat_address = interfaces[0].get('primaryV4Address', {}).get('oneToOneNat', {})
            if nat_address:
                ip_address = nat_address.get('address', 'N/A')
        
        print(f"  Имя: {vm_name}")
        print(f"  ID: {vm_id}")
        print(f"  Статус: {status}")
        print(f"  IP адрес: {ip_address}")
        print()
