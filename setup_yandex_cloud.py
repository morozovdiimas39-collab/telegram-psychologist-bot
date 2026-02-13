#!/usr/bin/env python3
"""
Скрипт для автоматической настройки инфраструктуры Yandex Cloud:
1. Создание Managed PostgreSQL
2. Настройка секретов в облачных функциях
3. Применение миграций БД
"""

import json
import os
import requests
import time
import sys

# Конфигурация
CONFIG = {
    'folder_id': None,  # Заполни вручную или получи через API
    'db_name': 'rsya_cleaner',
    'db_user': 'rsya_user',
    'db_password': None,  # Будет сгенерирован или введи вручную
    'cluster_name': 'rsya-db',
    'github_token': None,  # Введи свой GitHub токен
    'yandex_cloud_token': None,  # Введи свой Yandex Cloud OAuth токен
}

# Список функций, которым нужны секреты
FUNCTIONS_CONFIG = {
    'deploy-long': {
        'env': ['DATABASE_URL', 'GITHUB_TOKEN', 'MAIN_DB_SCHEMA'],
        'description': 'Деплой фронтенда на VM'
    },
    'deploy-functions': {
        'env': ['GITHUB_TOKEN', 'YANDEX_CLOUD_TOKEN'],
        'description': 'Деплой backend функций'
    },
    'migrate': {
        'env': ['DATABASE_URL', 'GITHUB_TOKEN'],
        'description': 'Применение миграций БД'
    },
    'deploy-config': {
        'env': ['DATABASE_URL', 'MAIN_DB_SCHEMA'],
        'description': 'Управление конфигами деплоя'
    },
    'vm-setup': {
        'env': ['DATABASE_URL', 'YANDEX_CLOUD_TOKEN', 'MAIN_DB_SCHEMA'],
        'description': 'Создание VM'
    },
    'vm-list': {
        'env': ['DATABASE_URL', 'MAIN_DB_SCHEMA'],
        'description': 'Список VM'
    },
    'yc-sync': {
        'env': ['DATABASE_URL', 'YANDEX_CLOUD_TOKEN', 'MAIN_DB_SCHEMA'],
        'description': 'Синхронизация VM с Yandex Cloud'
    },
    'deploy-status': {
        'env': ['DATABASE_URL', 'MAIN_DB_SCHEMA'],
        'description': 'Статус деплоя'
    },
}


def get_iam_token(oauth_token: str) -> str:
    """Получить IAM токен из OAuth токена"""
    resp = requests.post(
        'https://iam.api.cloud.yandex.net/iam/v1/tokens',
        json={'yandexPassportOauthToken': oauth_token},
        timeout=10
    )
    if resp.status_code != 200:
        raise Exception(f'Ошибка получения IAM токена: {resp.text}')
    return resp.json()['iamToken']


def get_folder_id(iam_token: str) -> str:
    """Получить folder_id"""
    headers = {'Authorization': f'Bearer {iam_token}'}
    
    # Получаем список облаков
    clouds_resp = requests.get(
        'https://resource-manager.api.cloud.yandex.net/resource-manager/v1/clouds',
        headers=headers,
        timeout=10
    )
    if clouds_resp.status_code != 200:
        raise Exception(f'Ошибка получения облаков: {clouds_resp.text}')
    
    clouds = clouds_resp.json().get('clouds', [])
    if not clouds:
        raise Exception('Не найдено облаков в аккаунте')
    
    cloud_id = clouds[0]['id']
    
    # Получаем список папок
    folders_resp = requests.get(
        f'https://resource-manager.api.cloud.yandex.net/resource-manager/v1/folders?cloudId={cloud_id}',
        headers=headers,
        timeout=10
    )
    if folders_resp.status_code != 200:
        raise Exception(f'Ошибка получения папок: {folders_resp.text}')
    
    folders = folders_resp.json().get('folders', [])
    if not folders:
        raise Exception('Не найдено папок в облаке')
    
    return folders[0]['id']


def create_managed_postgresql(iam_token: str, folder_id: str, config: dict) -> dict:
    """Создать Managed PostgreSQL кластер"""
    headers = {
        'Authorization': f'Bearer {iam_token}',
        'Content-Type': 'application/json'
    }
    
    # Проверяем существующие кластеры
    clusters_resp = requests.get(
        f'https://mdb.api.cloud.yandex.net/mdb/postgresql/v1/clusters?folderId={folder_id}',
        headers=headers,
        timeout=10
    )
    
    if clusters_resp.status_code == 200:
        clusters = clusters_resp.json().get('clusters', [])
        for cluster in clusters:
            if cluster['name'] == config['cluster_name']:
                print(f"✅ Кластер {config['cluster_name']} уже существует")
                return cluster
    
    print(f"📦 Создаю Managed PostgreSQL кластер {config['cluster_name']}...")
    
    # Создаём кластер
    cluster_payload = {
        'folderId': folder_id,
        'name': config['cluster_name'],
        'environment': 'PRODUCTION',
        'networkId': None,  # Нужно получить network_id
        'config': {
            'version': '15',
            'resources': {
                'resourcePresetId': 's2.micro',
                'diskTypeId': 'network-ssd',
                'diskSize': 10737418240  # 10 GB
            },
            'access': {
                'dataLens': False,
                'webSql': False,
                'serverless': False
            },
            'backupWindowStart': {
                'hours': 3,
                'minutes': 0
            },
            'performanceDiagnostics': {
                'enabled': False
            }
        },
        'databaseSpecs': [{
            'name': config['db_name'],
            'owner': config['db_user']
        }],
        'userSpecs': [{
            'name': config['db_user'],
            'password': config['db_password']
        }],
        'hostSpecs': [{
            'zoneId': 'ru-central1-a',
            'assignPublicIp': True
        }]
    }
    
    # Сначала нужно получить network_id
    # Для упрощения используем существующую сеть или создаём новую
    networks_resp = requests.get(
        f'https://vpc.api.cloud.yandex.net/vpc/v1/networks?folderId={folder_id}',
        headers=headers,
        timeout=10
    )
    
    if networks_resp.status_code == 200:
        networks = networks_resp.json().get('networks', [])
        if networks:
            cluster_payload['networkId'] = networks[0]['id']
        else:
            print("⚠️  Сеть не найдена. Нужно создать сеть вручную или через terraform.")
            return None
    
    create_resp = requests.post(
        'https://mdb.api.cloud.yandex.net/mdb/postgresql/v1/clusters',
        headers=headers,
        json=cluster_payload,
        timeout=30
    )
    
    if create_resp.status_code not in [200, 201]:
        print(f"❌ Ошибка создания кластера: {create_resp.text}")
        return None
    
    operation_id = create_resp.json().get('id')
    print(f"⏳ Кластер создаётся (operation: {operation_id})...")
    print("   Это может занять 5-10 минут...")
    
    # Ждём завершения операции
    for i in range(60):
        time.sleep(10)
        op_resp = requests.get(
            f'https://operation.api.cloud.yandex.net/operations/{operation_id}',
            headers=headers,
            timeout=10
        )
        if op_resp.status_code == 200:
            op_data = op_resp.json()
            if op_data.get('done'):
                print("✅ Кластер создан!")
                break
        print(f"   Ожидание... ({i+1}/60)")
    
    # Получаем информацию о кластере
    clusters_resp = requests.get(
        f'https://mdb.api.cloud.yandex.net/mdb/postgresql/v1/clusters?folderId={folder_id}',
        headers=headers,
        timeout=10
    )
    clusters = clusters_resp.json().get('clusters', [])
    for cluster in clusters:
        if cluster['name'] == config['cluster_name']:
            return cluster
    
    return None


def get_function_id(iam_token: str, folder_id: str, function_name: str) -> str:
    """Получить ID функции по имени"""
    headers = {'Authorization': f'Bearer {iam_token}'}
    
    resp = requests.get(
        f'https://serverless-functions.api.cloud.yandex.net/functions/v1/functions?folderId={folder_id}',
        headers=headers,
        timeout=10
    )
    
    if resp.status_code != 200:
        return None
    
    functions = resp.json().get('functions', [])
    for func in functions:
        if func['name'] == function_name:
            return func['id']
    
    return None


def update_function_env(iam_token: str, function_id: str, env_vars: dict):
    """Обновить переменные окружения функции"""
    headers = {
        'Authorization': f'Bearer {iam_token}',
        'Content-Type': 'application/json'
    }
    
    # Получаем текущую версию функции
    func_resp = requests.get(
        f'https://serverless-functions.api.cloud.yandex.net/functions/v1/functions/{function_id}',
        headers=headers,
        timeout=10
    )
    
    if func_resp.status_code != 200:
        print(f"   ⚠️  Не удалось получить информацию о функции")
        return False
    
    # Получаем последнюю версию
    versions_resp = requests.get(
        f'https://serverless-functions.api.cloud.yandex.net/functions/v1/versions?functionId={function_id}&pageSize=1',
        headers=headers,
        timeout=10
    )
    
    if versions_resp.status_code != 200:
        print(f"   ⚠️  Не удалось получить версии функции")
        return False
    
    versions = versions_resp.json().get('versions', [])
    if not versions:
        print(f"   ⚠️  У функции нет версий")
        return False
    
    latest_version = versions[0]
    
    # Обновляем переменные окружения
    current_env = latest_version.get('environment', {}) or {}
    updated_env = {**current_env, **env_vars}
    
    # Создаём новую версию с обновлёнными переменными
    # (в Yandex Cloud нельзя редактировать существующую версию)
    print(f"   ℹ️  Для обновления переменных нужно создать новую версию функции")
    print(f"   ℹ️  Сделай это вручную в консоли Yandex Cloud или через API")
    
    return True


def main():
    print("🚀 Настройка инфраструктуры Yandex Cloud")
    print("=" * 60)
    print()
    
    # Проверяем конфигурацию
    if not CONFIG['yandex_cloud_token']:
        print("❌ Укажи YANDEX_CLOUD_TOKEN в CONFIG")
        print("   Получи его здесь: https://oauth.yandex.ru/")
        sys.exit(1)
    
    if not CONFIG['github_token']:
        print("❌ Укажи GITHUB_TOKEN в CONFIG")
        print("   Создай здесь: https://github.com/settings/tokens")
        sys.exit(1)
    
    if not CONFIG['db_password']:
        import secrets
        CONFIG['db_password'] = secrets.token_urlsafe(16)
        print(f"🔑 Сгенерирован пароль БД: {CONFIG['db_password']}")
        print("   СОХРАНИ ЕГО!")
        print()
    
    # Получаем IAM токен
    print("🔐 Получаю IAM токен...")
    try:
        iam_token = get_iam_token(CONFIG['yandex_cloud_token'])
        print("✅ IAM токен получен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)
    
    # Получаем folder_id
    if not CONFIG['folder_id']:
        print("📁 Получаю folder_id...")
        try:
            CONFIG['folder_id'] = get_folder_id(iam_token)
            print(f"✅ Folder ID: {CONFIG['folder_id']}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            sys.exit(1)
    
    print()
    print("=" * 60)
    print("📋 Инструкция по настройке:")
    print("=" * 60)
    print()
    print("1. Создай Managed PostgreSQL вручную через консоль:")
    print("   https://console.cloud.yandex.ru/folders/{}/managed-postgresql/clusters".format(CONFIG['folder_id']))
    print()
    print("2. После создания БД получи DATABASE_URL:")
    print("   postgresql://{}:{}@FQDN_ХОСТА:6432/{}?sslmode=require".format(
        CONFIG['db_user'], CONFIG['db_password'], CONFIG['db_name']
    ))
    print()
    print("3. Настрой переменные окружения для функций:")
    print()
    
    for func_name, func_config in FUNCTIONS_CONFIG.items():
        print(f"   📦 {func_name} ({func_config['description']}):")
        for env_var in func_config['env']:
            if env_var == 'DATABASE_URL':
                print(f"      {env_var} = postgresql://{CONFIG['db_user']}:ПАРОЛЬ@ХОСТ:6432/{CONFIG['db_name']}?sslmode=require")
            elif env_var == 'GITHUB_TOKEN':
                print(f"      {env_var} = твой_github_token")
            elif env_var == 'YANDEX_CLOUD_TOKEN':
                print(f"      {env_var} = {CONFIG['yandex_cloud_token'][:20]}...")
            elif env_var == 'MAIN_DB_SCHEMA':
                print(f"      {env_var} = public (опционально)")
        print()
    
    print("=" * 60)
    print()
    print("💡 После настройки:")
    print("   1. В деплойере нажми 'Применить миграции БД'")
    print("   2. Проверь что таблицы созданы в БД")
    print()


if __name__ == '__main__':
    main()
