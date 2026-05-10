#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 usuario@IP_PUBLICA [ruta_remota]" >&2
  exit 1
fi

REMOTE="$1"
REMOTE_DIR="${2:-/opt/quiniela_predictor_mx}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ARCHIVE="/tmp/quiniela_predictor_mx_$(date +%Y%m%d_%H%M%S).tar.gz"

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  echo "ERROR: falta .env. Copia .env.example a .env y completa secretos antes de desplegar." >&2
  exit 1
fi

if grep -Eq '^(APP_SECRET_KEY|SESSION_SECRET|AUTH_PASSWORD_HASH)=$' "$ROOT_DIR/.env"; then
  echo "ERROR: .env tiene secretos obligatorios vacios." >&2
  exit 1
fi

tar \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='.pytest_cache' \
  --exclude='data/raw/*' \
  --exclude='data/processed/*' \
  --exclude='data/current/*' \
  --exclude='data/source_cache/*' \
  --exclude='data/prediction_logs/*' \
  --exclude='data/security_logs/*' \
  --exclude='data/active_draws/cache/*' \
  --exclude='data/active_draws/logs/*' \
  --exclude='data/active_draws/snapshots/*' \
  -czf "$ARCHIVE" -C "$ROOT_DIR" .

ssh "$REMOTE" "sudo mkdir -p '$REMOTE_DIR' && sudo chown -R \$(id -un):\$(id -gn) '$REMOTE_DIR'"
scp "$ARCHIVE" "$REMOTE:/tmp/quiniela_predictor_mx.tar.gz"
ssh "$REMOTE" "cd '$REMOTE_DIR' && tar -xzf /tmp/quiniela_predictor_mx.tar.gz && rm -f /tmp/quiniela_predictor_mx.tar.gz && chmod +x infra/scripts/*.sh && docker compose up -d --build && docker compose ps"

rm -f "$ARCHIVE"
echo "Deploy completado en $REMOTE:$REMOTE_DIR"
