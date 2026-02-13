#!/bin/bash
# Деплой ТОЛЬКО функции migrate из локальной папки
# Требует: yc CLI (yc config list должен работать)

set -e
cd "$(dirname "$0")/.."

# ID функции из URL: functions.yandexcloud.net/d4eoo7gt252g039lr5bj
FUNC_ID="${MIGRATE_FUNCTION_ID:-d4eoo7gt252g039lr5bj}"
FUNC_DIR="backend/migrate"

echo "📦 Деплою migrate (ID: $FUNC_ID) из $FUNC_DIR ..."

# Создаём zip
ZIP_FILE="/tmp/migrate-deploy.zip"
rm -f "$ZIP_FILE"
cd "$FUNC_DIR"
zip -q "$ZIP_FILE" index.py requirements.txt
cd - >/dev/null

echo "  Zip: $(ls -la $ZIP_FILE | awk '{print $5}') bytes"

yc serverless function version create \
  --function-id="$FUNC_ID" \
  --runtime=python312 \
  --entrypoint=handler.handler \
  --memory=256m \
  --execution-timeout=60s \
  --source-path="$ZIP_FILE"

rm -f "$ZIP_FILE"
echo "✅ migrate обновлена!"
