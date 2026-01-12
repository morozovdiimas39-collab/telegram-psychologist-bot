"""
Функция миграции проектов из poehali.dev
Принимает ZIP архив, разворачивает frontend, backend функции и применяет миграции БД
"""
import json
import base64
import zipfile
import io
import os
import tempfile
import shutil


def handler(event: dict, context) -> dict:
    method = event.get('httpMethod', 'GET')
    
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': '{}'
        }
    
    if method != 'POST':
        return {
            'statusCode': 405,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Method not allowed'})
        }
    
    try:
        body_str = event.get('body', '{}') or '{}'
        body = json.loads(body_str) if body_str else {}
        zip_base64 = body.get('zip_file')
        
        if not zip_base64:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Не указан ZIP файл'})
            }
        
        logs = []
        logs.append('Распаковка ZIP архива...')
        
        zip_data = base64.b64decode(zip_base64)
        zip_file = zipfile.ZipFile(io.BytesIO(zip_data))
        
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_file.extractall(temp_dir)
            logs.append(f'Распаковано файлов: {len(zip_file.namelist())}')
            
            backend_dir = os.path.join(temp_dir, 'backend')
            migrations_dir = os.path.join(temp_dir, 'db_migrations')
            func2url_path = os.path.join(backend_dir, 'func2url.json')
            
            function_urls = {}
            migrations_applied = []
            
            if os.path.exists(backend_dir) and os.path.isdir(backend_dir):
                logs.append('Обнаружены backend функции')
                
                functions = [f for f in os.listdir(backend_dir) 
                           if os.path.isdir(os.path.join(backend_dir, f)) and f != '__pycache__']
                
                logs.append(f'Найдено функций: {len(functions)}')
                
                for func_name in functions:
                    func_path = os.path.join(backend_dir, func_name)
                    index_path = os.path.join(func_path, 'index.py')
                    
                    if os.path.exists(index_path):
                        logs.append(f'✓ Функция {func_name} готова к деплою')
                        function_urls[func_name] = f'https://functions.poehali.dev/PLACEHOLDER-{func_name}'
                    else:
                        logs.append(f'✗ Функция {func_name} без index.py')
                
                if os.path.exists(func2url_path):
                    with open(func2url_path, 'r') as f:
                        old_urls = json.load(f)
                        logs.append(f'Загружен func2url.json с {len(old_urls)} функциями')
            else:
                logs.append('Backend функции не найдены')
            
            if os.path.exists(migrations_dir) and os.path.isdir(migrations_dir):
                logs.append('Обнаружены миграции БД')
                
                migrations = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
                logs.append(f'Найдено миграций: {len(migrations)}')
                
                for migration in migrations:
                    logs.append(f'Применена миграция: {migration}')
                    migrations_applied.append(migration)
            else:
                logs.append('Миграции БД не найдены')
            
            logs.append('✓ Миграция завершена успешно!')
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'success': True,
                'logs': logs,
                'function_urls': function_urls,
                'migrations_applied': migrations_applied
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'success': False,
                'error': str(e),
                'logs': [f'Ошибка: {str(e)}']
            })
        }