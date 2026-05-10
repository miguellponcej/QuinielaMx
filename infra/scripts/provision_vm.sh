#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TF_DIR="$ROOT_DIR/infra/terraform"

if ! command -v terraform >/dev/null 2>&1; then
  echo "ERROR: terraform no esta instalado." >&2
  exit 1
fi

if [[ -z "${DIGITALOCEAN_TOKEN:-}" ]]; then
  echo "ERROR: falta DIGITALOCEAN_TOKEN." >&2
  echo "Exporta el token: export DIGITALOCEAN_TOKEN='dop_v1_...'" >&2
  exit 1
fi

cd "$TF_DIR"
terraform init
terraform apply \
  -var "digitalocean_token=${DIGITALOCEAN_TOKEN}" \
  "$@"

terraform output
