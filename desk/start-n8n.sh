#!/usr/bin/env bash
# Run the pinned n8n locally without Docker (Node.js 22+). Same settings as docker-compose.yml.
cd "$(dirname "$0")/.."
export N8N_USER_FOLDER="$PWD/.n8n-local" N8N_PORT=5678 GENERIC_TIMEZONE=Asia/Dubai TZ=Asia/Dubai \
       N8N_DIAGNOSTICS_ENABLED=false N8N_PERSONALIZATION_ENABLED=false N8N_VERSION_NOTIFICATIONS_ENABLED=false \
       NODE_FUNCTION_ALLOW_BUILTIN=fs,path N8N_BLOCK_ENV_ACCESS_IN_NODE=false \
       DESK_DIR="$PWD/desk/runtime" SITE_DIR="$PWD/site" PIPELINE_URL="http://127.0.0.1:8765"
exec npx --yes n8n@2.42.5 start
