#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-/opt/quiniela_predictor_mx}"

echo "Disco:"
df -h /
echo
echo "Memoria:"
free -h
echo
echo "Docker:"
systemctl status docker --no-pager | sed -n '1,12p' || true
echo
echo "Nginx:"
systemctl status nginx --no-pager | sed -n '1,12p' || true
echo
echo "Contenedores:"
if [[ -d "$PROJECT_DIR" ]]; then
  cd "$PROJECT_DIR"
  docker compose ps || true
  echo
  echo "Health local Streamlit:"
  curl -fsS http://localhost:8501/_stcore/health || true
  echo
  echo "Nginx local:"
  curl -I --max-time 5 http://127.0.0.1 || true
  echo
  echo "Bloqueo de archivos sensibles:"
  curl -I --max-time 5 http://127.0.0.1/.env || true
  curl -I --max-time 5 http://127.0.0.1/data/ || true
  echo
  echo "Ultimos logs app:"
  docker compose logs --tail=80 quiniela-predictor || true
else
  echo "Proyecto no encontrado en $PROJECT_DIR"
fi
echo
"$(dirname "$0")/get_public_url.sh" "$PROJECT_DIR" || true
