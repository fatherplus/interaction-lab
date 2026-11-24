#!/usr/bin/env bash
# 发布 Interaction Lab 到一台已初始化好的 Docker 服务器。
#
# 服务器首次部署请先看 docs/DEPLOY.md（建目录、写 .env、放 Caddyfile）。
# 之后每次发布只需要：
#
#   deploy/deploy.sh user@ilab.example.com
#   deploy/deploy.sh user@1.2.3.4 --dir /srv/interaction-lab --domain ilab.example.com
#
# 依赖：本地 rsync + ssh；服务器 docker compose。
set -euo pipefail

HOST="${1:-}"
if [[ -z "$HOST" ]]; then
  echo "usage: $0 <user@host> [--dir /srv/interaction-lab] [--domain ilab.example.com] [--no-build]" >&2
  exit 2
fi
shift

REMOTE_DIR="/srv/interaction-lab"
DOMAIN=""
BUILD=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir) REMOTE_DIR="$2"; shift 2 ;;
    --domain) DOMAIN="$2"; shift 2 ;;
    --no-build) BUILD=0; shift ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> 同步源码到 $HOST:$REMOTE_DIR"
rsync -az --delete \
  --exclude '.git/' \
  --exclude 'dist/' \
  --exclude 'telemetry-data/' \
  --exclude 'mirror/' \
  --exclude '.impeccable/' \
  --exclude '.zcode/' \
  --exclude '__pycache__/' \
  --exclude '.env' \
  "$ROOT"/ "$HOST:$REMOTE_DIR"/

if [[ "$BUILD" == "1" ]]; then
  echo "==> 服务器端重建并重启"
  ssh "$HOST" "cd '$REMOTE_DIR' && docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml up -d --build"
else
  echo "==> 跳过重建（--no-build）"
fi

echo "==> 健康检查"
if [[ -n "$DOMAIN" ]]; then
  URL="https://$DOMAIN/api/health"
else
  URL="http://127.0.0.1:8900/api/health"
fi
ssh "$HOST" "for i in \$(seq 1 20); do
  if curl -fsS '$URL' >/dev/null 2>&1; then echo 'healthy: $URL'; exit 0; fi
  sleep 3
done
echo 'health check failed: $URL' >&2
docker compose -f '$REMOTE_DIR/docker-compose.yml' -f '$REMOTE_DIR/deploy/docker-compose.prod.yml' logs --tail=50 interaction-lab >&2
exit 1"
