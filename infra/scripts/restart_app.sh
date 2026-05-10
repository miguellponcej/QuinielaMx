#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-/opt/quiniela_predictor_mx}"
cd "$PROJECT_DIR"
docker compose down
docker compose up -d --build
docker compose ps
