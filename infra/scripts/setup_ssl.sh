#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Uso: sudo $0 dominio correo_admin" >&2
  echo "Ejemplo: sudo $0 quiniela.example.com admin@example.com" >&2
  exit 1
fi

DOMAIN="$1"
EMAIL="$2"
NGINX_CONF="/etc/nginx/sites-available/quiniela_predictor.conf"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Ejecuta con sudo." >&2
  exit 1
fi

if [[ -f "$NGINX_CONF" ]]; then
  sed -i -E "s/server_name[[:space:]]+[^;]+;/server_name ${DOMAIN};/" "$NGINX_CONF"
fi

nginx -t
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" --redirect
systemctl reload nginx
systemctl status certbot.timer --no-pager || true
echo "HTTPS configurado: https://$DOMAIN"
