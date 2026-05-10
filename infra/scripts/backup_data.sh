#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-/opt/quiniela_predictor_mx}"
BACKUP_DIR="${2:-$PROJECT_DIR/backups}"
STAMP="$(date +%Y%m%d_%H%M%S)"
TARGET="$BACKUP_DIR/quiniela_data_$STAMP.tar.gz"

mkdir -p "$BACKUP_DIR"
cd "$PROJECT_DIR"

tar -czf "$TARGET" \
  data/raw \
  data/processed \
  data/current \
  data/source_cache \
  data/prediction_logs \
  data/security_logs \
  data/active_draws \
  2>/dev/null || true

chmod 600 "$TARGET"
echo "Backup creado: $TARGET"
