#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-/opt/quiniela_predictor_mx}"
DOMAIN="${DOMAIN_NAME:-}"

PUBLIC_IP="$(curl -fsS --max-time 3 https://api.ipify.org || true)"
if [[ -z "$PUBLIC_IP" ]]; then
  PUBLIC_IP="$(hostname -I | awk '{print $1}')"
fi

HTTP_URL="http://${DOMAIN:-$PUBLIC_IP}"
if [[ -n "$DOMAIN" ]]; then
  HTTPS_URL="https://${DOMAIN}"
else
  HTTPS_URL="https://${PUBLIC_IP}.sslip.io"
fi

echo "IP publica: ${PUBLIC_IP:-PENDIENTE}"
echo "Dominio: ${DOMAIN:-No configurado}"
echo "URL HTTP: $HTTP_URL"
echo "URL HTTPS: $HTTPS_URL"
echo
echo "Estado Nginx:"
systemctl is-active nginx || true
echo
echo "Estado Docker:"
systemctl is-active docker || true
echo
echo "Estado contenedor:"
if [[ -d "$PROJECT_DIR" ]]; then
  cd "$PROJECT_DIR"
  docker compose ps || true
else
  echo "Proyecto no encontrado en $PROJECT_DIR"
fi
echo
echo "Logs app: cd $PROJECT_DIR && docker compose logs -f --tail=100"
