"""
Функция применения миграций БД из GitHub репозитория
Читает SQL файлы из db_migrations/ и применяет их к базе данных
"""
import json
import os
import base64
from urllib.parse import parse_qs, urlparse
import requests
import psycopg2
from psycopg2.extras import RealDictCursor

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Max-Age': '86400',
}


def handler(event: dict, context) -> dict:
    try:
        if not isinstance(event, dict):
            event = {}
        # Поддержка формата AWS (httpMethod) и Yandex Cloud (requestMethod)
        method = event.get('httpMethod') or event.get('requestMethod') or 'POST'
        params = event.get('params')
        if isinstance(params, dict):
            method = params.get('http_method') or method

        if method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': '',
                'isBase64Encoded': False
            }

        # GET: github_repo из query params
        github_repo = None
        query = event.get('queryStringParameters') or (params if isinstance(params, dict) else {})
        if isinstance(query, dict):
            github_repo = query.get('github_repo')
            if isinstance(github_repo, list):
                github_repo = github_repo[0] if github_repo else None

        # Yandex Cloud: params может содержать query
        if not github_repo and isinstance(params, dict):
            q = params.get('query') or params.get('queryStringParameters') or {}
            if isinstance(q, dict):
                github_repo = q.get('github_repo')
                if isinstance(github_repo, list):
                    github_repo = github_repo[0] if github_repo else None

        # Парсим из requestUrl если есть (Yandex Cloud)
        if not github_repo:
            url = event.get('requestUrl') or event.get('url')
            if not url and isinstance(event.get('request'), dict):
                url = event['request'].get('url')
            if url:
                parsed = urlparse(url)
                qs = parse_qs(parsed.query)
                github_repo = qs.get('github_repo', [None])[0]

        if not github_repo:
            # POST: из body
            raw_body = event.get('body') or '{}'
            if isinstance(raw_body, dict):
                body = raw_body
            elif isinstance(raw_body, str):
                if event.get('isBase64Encoded'):
                    try:
                        raw_body = base64.b64decode(raw_body).decode('utf-8')
                    except Exception:
                        pass
                raw_body = (raw_body or '').strip()
                body = {}
                if raw_body:
                    if raw_body.startswith('{'):
                        try:
                            body = json.loads(raw_body)
                        except json.JSONDecodeError:
                            body = {}
                    else:
                        parsed = parse_qs(raw_body)
                        body = {k: v[0] if v else '' for k, v in parsed.items()}
            else:
                body = {}
            github_repo = body.get('github_repo') or event.get('github_repo')
        
        if not github_repo:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', **CORS_HEADERS},
                'body': json.dumps({'error': 'Укажи github_repo'}),
                'isBase64Encoded': False
            }
        
        github_token = os.environ.get('GITHUB_TOKEN')
        if not github_token:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', **CORS_HEADERS},
                'body': json.dumps({'error': 'GITHUB_TOKEN не настроен'}),
                'isBase64Encoded': False
            }
        
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', **CORS_HEADERS},
                'body': json.dumps({'error': 'DATABASE_URL не настроен'}),
                'isBase64Encoded': False
            }
        
        logs = []
        logs.append("🔐 Подключаюсь к GitHub...")
        
        headers_gh = {
            'Authorization': f'Bearer {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Получаем информацию о репозитории
        repo_url = f'https://api.github.com/repos/{github_repo}'
        repo_resp = requests.get(repo_url, headers=headers_gh, timeout=10)
        
        if repo_resp.status_code != 200:
            logs.append(f"❌ Репозиторий недоступен: {repo_resp.status_code}")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', **CORS_HEADERS},
                'body': json.dumps({'error': f'Репозиторий {github_repo} недоступен', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        repo_data = repo_resp.json()
        default_branch = repo_data.get('default_branch', 'main')
        logs.append(f"✓ Репозиторий найден, ветка: {default_branch}")
        
        # Получаем список файлов миграций
        migrations_url = f'https://api.github.com/repos/{github_repo}/contents/db_migrations?ref={default_branch}'
        migrations_resp = requests.get(migrations_url, headers=headers_gh, timeout=10)
        
        if migrations_resp.status_code != 200:
            logs.append(f"⚠️ Папка db_migrations не найдена в репозитории")
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', **CORS_HEADERS},
                'body': json.dumps({
                    'success': True,
                    'logs': logs,
                    'migrations_applied': [],
                    'message': 'Миграции не найдены в репозитории'
                }),
                'isBase64Encoded': False
            }
        
        migration_files = migrations_resp.json()
        sql_files = [f for f in migration_files if f['type'] == 'file' and f['name'].endswith('.sql')]
        sql_files.sort(key=lambda x: x['name'])
        
        logs.append(f"📦 Найдено миграций: {len(sql_files)}")
        
        if len(sql_files) == 0:
            logs.append("ℹ️ SQL файлы не найдены в db_migrations/")
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', **CORS_HEADERS},
                'body': json.dumps({
                    'success': True,
                    'logs': logs,
                    'migrations_applied': []
                }),
                'isBase64Encoded': False
            }
        
        # Подключаемся к БД
        logs.append("🗄️ Подключаюсь к базе данных...")
        conn = psycopg2.connect(database_url)
        conn.autocommit = True  # с самого начала — иначе set_session внутри транзакции выдаёт ошибку
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Создаём таблицу для отслеживания применённых миграций
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Получаем список уже применённых миграций
        cur.execute("SELECT version FROM schema_migrations ORDER BY version")
        applied_versions = {row['version'] for row in cur.fetchall()}
        logs.append(f"📋 Уже применено миграций: {len(applied_versions)}")
        logs.append("")
        
        applied_count = 0
        skipped_count = 0
        failed_count = 0
        applied_migrations = []
        
        # Применяем миграции по порядку
        for migration_file in sql_files:
            migration_name = migration_file['name']
            migration_version = migration_name.split('__')[0] if '__' in migration_name else migration_name
            
            if migration_version in applied_versions:
                logs.append(f"⏭️  {migration_name} (уже применена)")
                skipped_count += 1
                continue
            
            logs.append(f"📝 Применяю {migration_name}...")
            
            try:
                # Читаем содержимое миграции из GitHub
                file_url = migration_file['download_url']
                file_resp = requests.get(file_url, headers=headers_gh, timeout=30)
                
                if file_resp.status_code != 200:
                    logs.append(f"   ❌ Не удалось прочитать файл: {file_resp.status_code}")
                    failed_count += 1
                    continue
                
                sql_content = file_resp.text
                
                try:
                    cur.execute(sql_content)
                    cur.execute(
                        "INSERT INTO schema_migrations (version) VALUES (%s) ON CONFLICT DO NOTHING",
                        (migration_version,)
                    )
                    logs.append(f"   ✅ Успешно применена")
                    applied_count += 1
                    applied_migrations.append(migration_name)
                    
                except psycopg2.errors.DuplicateTable:
                    logs.append(f"   ⏭️  (таблица уже существует)")
                    cur.execute(
                        "INSERT INTO schema_migrations (version) VALUES (%s) ON CONFLICT DO NOTHING",
                        (migration_version,)
                    )
                    skipped_count += 1
                    
                except psycopg2.errors.DuplicateObject:
                    logs.append(f"   ⏭️  (объект уже существует)")
                    cur.execute(
                        "INSERT INTO schema_migrations (version) VALUES (%s) ON CONFLICT DO NOTHING",
                        (migration_version,)
                    )
                    skipped_count += 1
                    
                except Exception as db_error:
                    error_msg = str(db_error)[:200]
                    logs.append(f"   ❌ Ошибка: {error_msg}")
                    failed_count += 1
                    
            except Exception as e:
                logs.append(f"   ❌ Ошибка чтения/применения: {str(e)[:200]}")
                failed_count += 1
        
        cur.close()
        conn.close()
        
        logs.append("")
        logs.append("=" * 60)
        logs.append(f"✅ Успешно применено: {applied_count} миграций")
        logs.append(f"⏭️  Пропущено (уже применены): {skipped_count} миграций")
        logs.append(f"❌ С ошибками: {failed_count} миграций")
        logs.append("=" * 60)
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', **CORS_HEADERS},
            'body': json.dumps({
                'success': True,
                'logs': logs,
                'migrations_applied': applied_migrations,
                'applied_count': applied_count,
                'skipped_count': skipped_count,
                'failed_count': failed_count
            }),
            'isBase64Encoded': False
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', **CORS_HEADERS},
            'body': json.dumps({
                'error': str(e),
                'logs': logs if 'logs' in locals() else [str(e)]
            }),
            'isBase64Encoded': False
        }
