import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import paramiko
import time


def _domain_ascii(domain: str) -> str:
    """Для IDN (кириллица и т.д.) возвращает punycode для certbot/nginx."""
    try:
        return domain.encode("idna").decode("ascii")
    except Exception:
        return domain


class _LogList(list):
    def append(self, x):
        super().append(x)
        print(x, flush=True)


def _ssh_run(ssh, cmd: str, timeout: int = 15) -> str:
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        stdout.channel.recv_exit_status()
    except Exception:
        pass
    out = stdout.read().decode("utf-8", errors="replace") if stdout else ""
    err = stderr.read().decode("utf-8", errors="replace") if stderr else ""
    return (out + err).strip()


def _prepare_certbot_idn_deploy_hook(ssh, domain: str, certbot_domain: str, nginx_site_name: str) -> None:
    """Подготовить certbot --deploy-hook: скрипт на сервере после выдачи серта подставит unicode в server_name (документация certbot)."""
    idn_line = f"{domain} {certbot_domain}"
    puny_sed = certbot_domain.replace(".", "\\.")
    hook_sh = f'''#!/bin/bash
export LANG=en_US.UTF-8
LINE=$(cat /tmp/nginx_idn_line.txt)
sed -i "s|server_name {puny_sed};|server_name $LINE;|g" /etc/nginx/sites-available/{nginx_site_name}
nginx -t && systemctl reload nginx
'''
    sftp = ssh.open_sftp()
    with sftp.file("/tmp/nginx_idn_line.txt", "wb") as f:
        f.write(idn_line.encode("utf-8"))
    with sftp.file("/tmp/nginx_idn_hook.sh", "wb") as f:
        f.write(hook_sh.encode("utf-8"))
    sftp.close()
    _ssh_run(ssh, "chmod +x /tmp/nginx_idn_hook.sh", timeout=5)


def handler(event: dict, context) -> dict:
    """Деплой проекта через SSH - для Яндекс Облака с увеличенным таймаутом"""
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
        if not body_str or body_str.strip() == '':
            body_str = '{}'
        body = json.loads(body_str) if isinstance(body_str, str) else body_str
        
        config_name = body.get('config_name')
        action = body.get('action', 'deploy')  # 'deploy' | 'setup_ssl'
        
        if not config_name:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Укажи config_name'}),
                'isBase64Encoded': False
            }
        
        dsn = os.environ['DATABASE_URL']
        schema = os.environ.get('MAIN_DB_SCHEMA', 'public')
        github_token = (body.get('github_token') or os.environ.get('GITHUB_TOKEN') or '').strip()
        
        conn = psycopg2.connect(dsn)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute(
            f"""
            SELECT dc.*, vm.ip_address, vm.ssh_user, vm.ssh_private_key, vm.name as vm_name
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
        
        logs = _LogList([
            f"🚀 Деплой: {config['domain']}",
            f"📦 Репо: {config['github_repo']}",
            ""
        ])
        
        if not config['vm_instance_id'] or not config['ip_address']:
            logs.append("❌ VM не привязана к конфигу")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'VM не привязана', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        vm_ip = config['ip_address']
        domain = config['domain']
        github_repo = config['github_repo']
        ssh_user = config['ssh_user'] or 'ubuntu'
        ssh_key = config['ssh_private_key']
        
        if not ssh_key:
            logs.append("❌ SSH ключ не найден в БД")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'SSH key missing', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        logs.append(f"🖥️  Сервер: {vm_ip}")
        logs.append(f"👤 Пользователь: {ssh_user}")
        logs.append("")
        logs.append("🔐 Подключаюсь по SSH...")
        
        # SSH подключение
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        from io import StringIO
        try:
            pkey = paramiko.RSAKey.from_private_key(StringIO(ssh_key))
        except Exception as key_error:
            logs.append(f"❌ Ошибка парсинга SSH ключа: {str(key_error)}")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Invalid SSH key format', 'logs': logs}),
                'isBase64Encoded': False
            }
        
        ssh.connect(
            hostname=vm_ip,
            username=ssh_user,
            pkey=pkey,
            timeout=30,
            allow_agent=False,
            look_for_keys=False
        )
        
        logs.append("✅ SSH подключение установлено")
        logs.append("")
        
        domain_ascii = _domain_ascii(domain)
        certbot_domain = domain_ascii if domain_ascii != domain else domain
        server_names = f"{domain} {certbot_domain}" if certbot_domain != domain else domain
        domain_safe = domain.replace('.', '_').replace('*', '_')
        nginx_site_name = certbot_domain.replace('.', '_') if certbot_domain != domain else domain_safe
        dir_safe = nginx_site_name if certbot_domain != domain else domain_safe

        if action == 'setup_ssl':
            logs.append("🔒 Режим: только установка SSL")
            logs.append("")
            nginx_t = _ssh_run(ssh, "sudo nginx -t 2>&1")
            if "conflicting server name" in nginx_t.lower():
                logs.append("⚠️ nginx: conflicting server name — удали дубликат конфига из sites-enabled.")
            for line in nginx_t.split("\n"):
                if "warn" in line.lower() or "error" in line.lower() or "conflicting" in line.lower() or "successful" in line.lower():
                    logs.append(f"   {line.strip()}")
            logs.append("")
            stdin, stdout, stderr = ssh.exec_command("which certbot 2>/dev/null || echo ''")
            certbot_path = stdout.read().decode('utf-8').strip()
            if not certbot_path:
                logs.append("📦 Устанавливаю certbot...")
                stdin, stdout, stderr = ssh.exec_command("sudo apt-get update && sudo apt-get install -y certbot python3-certbot-nginx", timeout=120)
                stdout.channel.recv_exit_status()
                logs.append("✅ Certbot установлен")
            logs.append("🔒 Запускаю certbot...")
            if certbot_domain != domain:
                _prepare_certbot_idn_deploy_hook(ssh, domain, certbot_domain, nginx_site_name)
            certbot_cmd = f"sudo certbot --nginx -d {certbot_domain} --non-interactive --agree-tos --email admin@{certbot_domain}"
            if certbot_domain != domain:
                certbot_cmd += " --deploy-hook '/tmp/nginx_idn_hook.sh'"
            certbot_cmd += " 2>&1"
            stdin, stdout, stderr = ssh.exec_command(certbot_cmd, timeout=120)
            certbot_out = stdout.read().decode('utf-8')
            logs.append("")
            if 'Successfully received certificate' in certbot_out or 'Certificate not yet due for renewal' in certbot_out:
                logs.append("✅ SSL сертификат установлен!")
                logs.append(f"   Сайт: https://{domain}")
                if certbot_domain != domain:
                    _ssh_run(ssh, "sudo /tmp/nginx_idn_hook.sh", timeout=10)
                    _ssh_run(ssh, "sudo nginx -t 2>&1 && sudo systemctl reload nginx 2>&1", timeout=10)
            else:
                logs.append("📋 Вывод certbot:")
                for line in certbot_out.strip().split('\n')[-15:]:
                    logs.append(f"   {line}")
                if 'could not resolve' in certbot_out.lower() or 'dns' in certbot_out.lower():
                    logs.append("")
                    logs.append("⚠️ Настрой DNS A-запись: " + domain + " → " + vm_ip)
                if certbot_domain != domain:
                    logs.append("")
                    logs.append("💡 Если SSL не появился — на сервере по SSH выполни:")
                    logs.append(f"   sudo certbot --nginx -d {certbot_domain} --non-interactive --agree-tos -m admin@{certbot_domain}")
                    logs.append(f"   sudo nginx -t && sudo systemctl reload nginx")
            ssh.close()
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'success': True, 'logs': logs, 'url': f"https://{domain}"}),
                'isBase64Encoded': False
            }
        
        project_dir = f"/var/www/{dir_safe}"
        
        # Проверяем и устанавливаем git если нужно
        logs.append("🔍 Проверяю git...")
        stdin, stdout, stderr = ssh.exec_command("which git", timeout=10)
        git_path = stdout.read().decode('utf-8').strip()
        
        if not git_path:
            logs.append("📦 Устанавливаю git...")
            stdin, stdout, stderr = ssh.exec_command("sudo apt-get update && sudo apt-get install -y git", timeout=120)
            exit_code = stdout.channel.recv_exit_status()
            if exit_code != 0:
                logs.append(f"❌ Не удалось установить git: {stderr.read().decode('utf-8')}")
                ssh.close()
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'git installation failed', 'logs': logs}),
                    'isBase64Encoded': False
                }
            logs.append("✅ Git установлен")
        else:
            logs.append(f"✅ Git найден: {git_path}")
        
        logs.append("")
        
        # Клонируем репо
        logs.append("📥 Клонирую репозиторий...")
        
        # Нормализуем github_repo (может быть полный URL или owner/repo)
        if github_repo.startswith('http://') or github_repo.startswith('https://'):
            # Извлекаем owner/repo из полного URL
            import re
            match = re.search(r'github\.com[/:]([^/]+/[^/]+?)(?:\.git)?/?$', github_repo)
            if match:
                github_repo = match.group(1)
            else:
                logs.append(f"⚠️ Не удалось извлечь owner/repo из URL: {github_repo}")
        
        # Убираем .git если есть
        github_repo = github_repo.rstrip('/').rstrip('.git')
        
        clone_url = f"https://{github_token}@github.com/{github_repo}.git" if github_token else f"https://github.com/{github_repo}.git"
        logs.append(f"   Репозиторий: {github_repo}")
        
        # Чистим старый мусор деплоев до clone (чтобы не упираться в No space left on device).
        cleanup_cmd = (
            "sudo find /var/www -maxdepth 1 -type d "
            "\\( -name '*.new_*' -o -name '*.old_*' \\) "
            "-mtime +1 -print -exec rm -rf {} + 2>/dev/null || true"
        )
        _ssh_run(ssh, cleanup_cmd, timeout=20)
        _ssh_run(ssh, "sudo journalctl --vacuum-time=7d >/dev/null 2>&1 || true", timeout=20)
        _ssh_run(ssh, "sudo apt-get clean >/dev/null 2>&1 || true", timeout=20)

        prep_commands = [
            f"sudo systemctl stop next_{dir_safe}.service 2>/dev/null || true",
            f"sudo rm -rf '{project_dir}'",
            f"sudo mkdir -p '{project_dir}'",
            f"sudo chown -R {ssh_user}:{ssh_user} '{project_dir}'",
        ]
        for cmd in prep_commands:
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
            exit_code = stdout.channel.recv_exit_status()
            if exit_code != 0:
                error = stderr.read().decode('utf-8')
                logs.append(f"❌ Ошибка: {cmd[:80]}...")
                logs.append(f"   {error}")
                ssh.close()
                return {'statusCode': 500, 'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}, 'body': json.dumps({'error': error, 'logs': logs}), 'isBase64Encoded': False}

        # Пробуем clone; при нехватке места делаем расширенную очистку и повторяем один раз.
        clone_cmd = f"git clone {clone_url} '{project_dir}'"
        stdin, stdout, stderr = ssh.exec_command(clone_cmd, timeout=90)
        clone_exit = stdout.channel.recv_exit_status()
        if clone_exit != 0:
            clone_err = stderr.read().decode('utf-8')
            if "No space left on device" in clone_err:
                logs.append("⚠️ Недостаточно места на диске. Чищу /var/www и повторяю clone...")
                _ssh_run(ssh, "sudo find /var/www -maxdepth 1 -type d \\( -name '*.new_*' -o -name '*.old_*' \\) -print -exec rm -rf {} + 2>/dev/null || true", timeout=30)
                _ssh_run(ssh, "sudo journalctl --vacuum-size=200M >/dev/null 2>&1 || true", timeout=20)
                _ssh_run(ssh, "sudo rm -rf /tmp/* 2>/dev/null || true", timeout=20)
                stdin, stdout, stderr = ssh.exec_command(clone_cmd, timeout=90)
                clone_exit = stdout.channel.recv_exit_status()
                if clone_exit != 0:
                    clone_err = stderr.read().decode('utf-8')
            if clone_exit != 0:
                logs.append(f"❌ Ошибка: {clone_cmd[:80]}...")
                logs.append(f"   {clone_err}")
                ssh.close()
                return {'statusCode': 500, 'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}, 'body': json.dumps({'error': clone_err, 'logs': logs}), 'isBase64Encoded': False}
        
        logs.append("✅ Репозиторий склонирован")
        logs.append("")
        
        log_path = f"/tmp/deploy_{domain}.log"
        mode_file = f"/tmp/deploy_mode_{dir_safe}"
        next_port = 3000 + (sum(ord(c) for c in dir_safe) % 500)
        # Если в start-скрипте есть явный порт (-p/--port), используем его.
        detect_port_cmd = f"""python3 - <<'PY'
import json, re
try:
    p = "{project_dir}/package.json"
    with open(p, "r", encoding="utf-8") as f:
        s = (((json.load(f) or {{}}).get("scripts") or {{}}).get("start") or "")
    m = re.search(r"(?:--port|-p)\\s+(\\d{{2,5}})", s)
    print(m.group(1) if m else "")
except Exception:
    print("")
PY"""
        stdin, stdout, stderr = ssh.exec_command(detect_port_cmd, timeout=10)
        explicit_port = (stdout.read().decode("utf-8").strip() or "")
        if explicit_port.isdigit():
            p = int(explicit_port)
            if 1 <= p <= 65535:
                next_port = p
        
        deploy_script = f"""#!/bin/bash
set -e
cd {project_dir}
LOG={log_path}
DOMAIN_SAFE="{dir_safe}"
: > "$LOG"
DEPLOY_MODE="static"
RAM_MB=$(free -m | awk '/^Mem:/{{print $2}}')
SWAP_MB=$(free -m | awk '/^Swap:/{{print $2}}')
if [ "$RAM_MB" -lt 2048 ] 2>/dev/null && [ "$SWAP_MB" -lt 1500 ] 2>/dev/null; then
  echo "Мало RAM, создаю swap..." >> "$LOG"
  sudo fallocate -l 2G /swapfile 2>/dev/null || true
  [ -f /swapfile ] && sudo chmod 600 /swapfile && sudo mkswap /swapfile 2>/dev/null && sudo swapon /swapfile 2>/dev/null || true
fi
if [ -f ~/.nvm/nvm.sh ]; then . ~/.nvm/nvm.sh; nvm use 20 2>/dev/null || nvm use 18 2>/dev/null || true; fi
echo "Node: $(node -v 2>/dev/null)" >> "$LOG"
npm install >> "$LOG" 2>&1
echo "✅ Зависимости установлены" >> "$LOG"
OUT_DIR=""
if grep -q '"nuxt"' package.json 2>/dev/null || [ -f nuxt.config.ts ] || [ -f nuxt.config.js ]; then
  BUILD_CMD="npm run generate || npx nuxt generate"
  OUT_DIR=".output/public"
elif grep -q '"next"' package.json 2>/dev/null; then
  echo "🔨 Next.js build..." >> "$LOG"
  npm run build >> "$LOG" 2>&1
  if [ -d out ]; then
    sudo mkdir -p /var/www/{dir_safe}/html
    sudo cp -rT {project_dir}/out /var/www/{dir_safe}/html
  elif [ -d dist ]; then
    sudo mkdir -p /var/www/{dir_safe}/html
    sudo cp -rT {project_dir}/dist /var/www/{dir_safe}/html
  else
    DEPLOY_MODE="next"
    printf '%s\\n' '#!/bin/bash' 'cd {project_dir}' '[ -f ~/.nvm/nvm.sh ] && . ~/.nvm/nvm.sh' 'export PORT={next_port}' 'exec npm run start' > {project_dir}/start.sh
    chmod +x {project_dir}/start.sh
    printf '%s\\n' '[Unit]' 'Description=Next.js {domain}' 'After=network.target' '[Service]' 'Type=simple' 'User={ssh_user}' 'WorkingDirectory={project_dir}' 'Environment=PORT={next_port}' 'ExecStart={project_dir}/start.sh' 'Restart=always' '[Install]' 'WantedBy=multi-user.target' | sudo tee /etc/systemd/system/next_$DOMAIN_SAFE.service > /dev/null
    sudo systemctl daemon-reload
    sudo systemctl enable next_$DOMAIN_SAFE.service 2>/dev/null || true
    sudo systemctl restart next_$DOMAIN_SAFE.service
  fi
else
  BUILD_CMD="npm run build"
  OUT_DIR="dist"
fi
if [ -n "$OUT_DIR" ]; then
  eval $BUILD_CMD >> "$LOG" 2>&1
  sudo mkdir -p /var/www/{dir_safe}/html
  sudo cp -rT {project_dir}/$OUT_DIR /var/www/{dir_safe}/html
fi
if [ "$DEPLOY_MODE" = "static" ]; then
  sudo chown -R www-data:www-data /var/www/{dir_safe}/html
fi
echo "$DEPLOY_MODE" > {mode_file}
echo "✅ Деплой завершён $(date)" >> "$LOG"
"""
        
        sftp = ssh.open_sftp()
        script_path = f"/tmp/deploy_{domain.replace('.', '_')}.sh"
        with sftp.file(script_path, 'w') as f:
            f.write(deploy_script)
        sftp.close()
        ssh.exec_command(f"chmod +x {script_path}")
        
        www_domain = f"/var/www/{dir_safe}"
        stdin, stdout, stderr = ssh.exec_command(f"grep -q '\"next\"' {project_dir}/package.json 2>/dev/null && echo next || echo static")
        is_next = (stdout.read().decode("utf-8").strip() or "static") == "next"
        stdin, stdout, stderr = ssh.exec_command(f"sudo mkdir -p {www_domain} && sudo chmod 755 {www_domain}")
        stdout.channel.recv_exit_status()
        
        if is_next:
            logs.append(f"📦 Next.js: сборка в фоне, порт {next_port} (ответ сразу).")
            nginx_proxy = f"""server {{
    listen 80;
    server_name {server_names};
    access_log /var/log/nginx/{dir_safe}_access.log;
    error_log /var/log/nginx/{dir_safe}_error.log;
    location / {{
        proxy_pass http://127.0.0.1:{next_port};
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}"""
            tmp_nginx = f"/tmp/nginx_sites_{dir_safe}"
            sftp = ssh.open_sftp()
            with sftp.file(tmp_nginx, "wb") as f:
                f.write(nginx_proxy.encode("utf-8"))
            sftp.close()
            stdin, stdout, stderr = ssh.exec_command(f"sudo mv {tmp_nginx} /etc/nginx/sites-available/{nginx_site_name}")
            stdout.channel.recv_exit_status()
            stdin, stdout, stderr = ssh.exec_command(f"sudo ln -sf /etc/nginx/sites-available/{nginx_site_name} /etc/nginx/sites-enabled/{nginx_site_name}")
            stdout.channel.recv_exit_status()
            if certbot_domain != domain:
                logs.append("   Прописываю кириллический домен в nginx (deploy-hook после certbot)...")
                _prepare_certbot_idn_deploy_hook(ssh, domain, certbot_domain, nginx_site_name)
            certbot_cmd = f"sudo certbot --nginx -d {certbot_domain} --non-interactive --agree-tos --email admin@{certbot_domain}"
            if certbot_domain != domain:
                certbot_cmd += " --deploy-hook '/tmp/nginx_idn_hook.sh'"
            certbot_cmd += " 2>&1 || true"
            _ssh_run(ssh, certbot_cmd, timeout=120)
            if certbot_domain != domain:
                _ssh_run(ssh, "sudo /tmp/nginx_idn_hook.sh", timeout=10)
            if certbot_domain != domain:
                ssh.exec_command(f"sudo rm -f /etc/nginx/sites-enabled/{domain_safe}")
                _ssh_run(ssh, f"for p in $(sudo grep -l '{certbot_domain}' /etc/nginx/sites-available/* 2>/dev/null); do s=$(basename \"$p\"); [ \"$s\" = '{nginx_site_name}' ] && continue; sudo rm -f \"/etc/nginx/sites-enabled/$s\"; done", timeout=10)
                _ssh_run(ssh, f"for p in $(sudo grep -Fl -- '{domain}' /etc/nginx/sites-available/* 2>/dev/null); do s=$(basename \"$p\"); [ \"$s\" = '{nginx_site_name}' ] && continue; sudo rm -f \"/etc/nginx/sites-enabled/$s\"; done", timeout=10)
            stdin, stdout, stderr = ssh.exec_command("sudo nginx -t 2>/dev/null && sudo systemctl reload nginx 2>/dev/null || true")
            stdout.channel.recv_exit_status()
            ssh.exec_command(f"nohup bash {script_path} >> {log_path} 2>&1 &")
            time.sleep(1)
            logs.append("✅ Деплой запущен. Сборка 2–4 мин в фоне — обнови сайт через пару минут.")
            logs.append(f"   Открывай только по домену: https://{domain}  (не по IP)")
            logs.append(f"   Лог на сервере: tail -f {log_path}")
            ssh.close()
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'success': True, 'logs': logs, 'url': f"http://{domain}", 'ip_url': f"http://{vm_ip}"}),
                'isBase64Encoded': False
            }
        
        logs.append("📁 Готовлю каталог для сборки...")
        build_timeout = 280
        logs.append(f"🚀 Запускаю npm install + build (жду до {build_timeout} сек)...")
        stdin, stdout, stderr = ssh.exec_command(f"bash {script_path}")
        chan = stdout.channel
        chan.settimeout(build_timeout)
        try:
            exit_status = chan.recv_exit_status()
        except Exception as e:
            logs.append(f"❌ Таймаут сборки ({build_timeout} сек) или обрыв: {e}")
            stdin, stdout, stderr = ssh.exec_command(f"tail -80 {log_path} 2>/dev/null || true")
            for line in (stdout.read().decode("utf-8", errors="replace") or "(лог пуст)").strip().split("\n"):
                logs.append(f"   {line}")
            ssh.close()
            return {'statusCode': 500, 'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}, 'body': json.dumps({'error': 'Build timeout', 'logs': logs}), 'isBase64Encoded': False}
        if exit_status != 0:
            logs.append("❌ Сборка завершилась с ошибкой.")
            stdin, stdout, stderr = ssh.exec_command(f"tail -200 {log_path} 2>/dev/null || true")
            for line in (stdout.read().decode("utf-8", errors="replace") or "(лог пуст)").strip().split("\n"):
                logs.append(f"   {line}")
            ssh.close()
            return {'statusCode': 500, 'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}, 'body': json.dumps({'error': 'Build failed', 'logs': logs}), 'isBase64Encoded': False}
        logs.append("✅ Сборка завершена.")
        stdin, stdout, stderr = ssh.exec_command(f"cat {mode_file} 2>/dev/null || echo static")
        deploy_mode = (stdout.read().decode("utf-8").strip() or "static").lower()
        logs.append("")
        logs.append("⚙️ Настраиваю nginx...")
        nginx_config = f"""server {{
    listen 80;
    server_name {server_names};
    root /var/www/{dir_safe}/html;
    index index.html;
    access_log /var/log/nginx/{dir_safe}_access.log;
    error_log /var/log/nginx/{dir_safe}_error.log;
    location / {{ try_files $uri $uri/ /index.html; }}
    location ~* \\.(?:css|js|jpg|jpeg|gif|png|ico|svg|woff|woff2|ttf|eot)$ {{ expires 1y; access_log off; add_header Cache-Control "public, immutable"; }}
}}"""
        tmp_nginx = f"/tmp/nginx_sites_{dir_safe}"
        sftp = ssh.open_sftp()
        with sftp.file(tmp_nginx, "wb") as f:
            f.write(nginx_config.encode("utf-8"))
        sftp.close()
        stdin, stdout, stderr = ssh.exec_command(f"sudo mv {tmp_nginx} /etc/nginx/sites-available/{nginx_site_name}")
        stdout.channel.recv_exit_status()
        stdin, stdout, stderr = ssh.exec_command(f"sudo ln -sf /etc/nginx/sites-available/{nginx_site_name} /etc/nginx/sites-enabled/{nginx_site_name}")
        stdout.channel.recv_exit_status()
        if certbot_domain != domain:
            ssh.exec_command(f"sudo rm -f /etc/nginx/sites-enabled/{domain_safe}")
            _ssh_run(ssh, f"for p in $(sudo grep -l '{certbot_domain}' /etc/nginx/sites-available/* 2>/dev/null); do s=$(basename \"$p\"); [ \"$s\" = '{nginx_site_name}' ] && continue; sudo rm -f \"/etc/nginx/sites-enabled/$s\"; done", timeout=10)
            _ssh_run(ssh, f"for p in $(sudo grep -Fl -- '{domain}' /etc/nginx/sites-available/* 2>/dev/null); do s=$(basename \"$p\"); [ \"$s\" = '{nginx_site_name}' ] && continue; sudo rm -f \"/etc/nginx/sites-enabled/$s\"; done", timeout=10)
        stdin, stdout, stderr = ssh.exec_command("sudo nginx -t")
        if stdout.channel.recv_exit_status() != 0:
            logs.append(f"❌ nginx -t: {stderr.read().decode('utf-8')}")
        else:
            stdin, stdout, stderr = ssh.exec_command("sudo systemctl reload nginx")
            stdout.channel.recv_exit_status()
            logs.append(f"✅ nginx настроен для {domain}")
        logs.append("")
        logs.append("🔒 Certbot для SSL...")
        if certbot_domain != domain:
            _prepare_certbot_idn_deploy_hook(ssh, domain, certbot_domain, nginx_site_name)
        certbot_cmd = f"sudo certbot --nginx -d {certbot_domain} --non-interactive --agree-tos --email admin@{certbot_domain}"
        if certbot_domain != domain:
            certbot_cmd += " --deploy-hook '/tmp/nginx_idn_hook.sh'"
        certbot_cmd += " 2>&1 || true"
        stdin, stdout, stderr = ssh.exec_command(certbot_cmd)
        certbot_out = stdout.read().decode('utf-8')
        if 'Successfully received certificate' in certbot_out or 'Certificate not yet due for renewal' in certbot_out:
            logs.append("✅ SSL настроен")
        else:
            logs.append("⚠️ SSL: настрой DNS A-запись и перезапусти деплой")
        if certbot_domain != domain:
            _ssh_run(ssh, "sudo /tmp/nginx_idn_hook.sh", timeout=10)
            _ssh_run(ssh, f"for f in /etc/nginx/sites-enabled/*; do bn=$(basename \"$f\"); [ \"$bn\" = 'default' ] && continue; [ \"$bn\" = '{nginx_site_name}' ] && continue; t=$(sudo readlink -f \"$f\" 2>/dev/null); [ -n \"$t\" ] && [ -f \"$t\" ] && sudo sed -i 's/default_server//g' \"$t\"; done", timeout=10)
            _ssh_run(ssh, "sudo nginx -t 2>&1 && sudo systemctl reload nginx 2>&1", timeout=10)
        if deploy_mode == "next":
            _ssh_run(ssh, f"sudo systemctl restart next_{dir_safe}.service 2>&1", timeout=15)
        ssh.close()
        logs.append("")
        logs.append(f"🎉 Деплой завершён! Домен: {domain}, Сайт: https://{domain}")
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'success': True, 'logs': logs, 'url': f"http://{domain}", 'ip_url': f"http://{vm_ip}"}),
            'isBase64Encoded': False
        }
        
    except paramiko.SSHException as e:
        logs.append(f"❌ SSH ошибка: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': f'SSH failed: {str(e)}', 'logs': logs}),
            'isBase64Encoded': False
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)}),
            'isBase64Encoded': False
        }