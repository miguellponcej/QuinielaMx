# Despliegue privado de QuinielaPredictor MX

Esta guia despliega QuinielaPredictor MX en una VM Ubuntu 24.04 con Docker, Docker Compose, Nginx, UFW y HTTPS. La app sigue siendo privada por defecto: antes de cargar Home, predicciones, archivos, logs o reportes exige sesion autorizada.

## Arquitectura

```text
Internet
  -> IP publica o dominio
  -> Nginx reverse proxy con headers de seguridad
  -> Docker container en 127.0.0.1:8501
  -> Streamlit privado
  -> data/ persistente no publicado
```

## Requisitos previos

- Cuenta de DigitalOcean.
- Token API con permisos de escritura.
- Terraform instalado en la maquina desde donde crearas la VM.
- SSH key local, por defecto `~/.ssh/id_ed25519.pub`.
- Opcional: dominio o subdominio apuntando a la IP publica.

No se detectaron credenciales cloud en esta sesion. Para crear la VM debes exportar:

```bash
export DIGITALOCEAN_TOKEN="dop_v1_TU_TOKEN"
```

## Variables de entorno de la app

Copia el ejemplo:

```bash
cp .env.example .env
```

Genera secretos:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from src.auth.auth_service import hash_password; print(hash_password('TU_PASSWORD_SEGURO'))"
```

Completa al menos:

```text
APP_ENV=production
PRIVATE_BY_DEFAULT=true
APP_SECRET_KEY=<secreto-largo>
SESSION_SECRET=<secreto-largo>
AUTHORIZED_EMAILS=miguellponcej@gmail.com
AUTH_PASSWORD_HASH=pbkdf2_sha256$...
ACTIVE_DRAWS_REFRESH_MINUTES=60
```

Google OAuth queda preparado con `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET`, pero no es obligatorio si usas password hash. Nunca subas `.env` al repositorio.

## Crear la VM con Terraform

Desde la raiz del proyecto:

```bash
chmod +x infra/scripts/*.sh
export DIGITALOCEAN_TOKEN="dop_v1_TU_TOKEN"
infra/scripts/provision_vm.sh \
  -var "region=nyc3" \
  -var "droplet_name=quiniela-predictor-mx" \
  -var "domain_name="
```

Terraform crea:

- Droplet Ubuntu 24.04.
- Usuario no root `quiniela`.
- SSH key.
- Firewall cloud con 22, 80 y 443.
- Docker, Docker Compose, Nginx, Certbot y UFW por cloud-init.

Salida esperada:

```text
vm_public_ip = "123.123.123.123"
app_http_url = "http://123.123.123.123"
app_https_url = "https://123.123.123.123.sslip.io"
ssh_command = "ssh quiniela@123.123.123.123"
```

## Desplegar la app

Usa la IP entregada por Terraform:

```bash
infra/scripts/deploy_app.sh quiniela@IP_PUBLICA
```

Esto empaqueta el proyecto sin `.env`, sin `.venv`, sin caches ni datos sensibles, lo copia a `/opt/quiniela_predictor_mx`, construye la imagen y levanta Docker Compose.

## Configurar dominio

Si tienes dominio:

1. Crea un registro `A` hacia la IP publica.
2. Edita `/etc/nginx/sites-available/quiniela_predictor.conf` en la VM y reemplaza `server_name _;` por tu dominio.
3. Recarga Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Si no tienes dominio, puedes usar HTTP temporal:

```text
http://IP_PUBLICA
```

Para HTTPS sin dominio propio puedes apuntar Nginx a `IP_PUBLICA.sslip.io` y usar Certbot con ese host.

## Activar HTTPS

Con dominio real o `sslip.io`:

```bash
ssh quiniela@IP_PUBLICA
sudo DOMAIN_NAME=IP_PUBLICA.sslip.io /opt/quiniela_predictor_mx/infra/scripts/setup_ssl.sh IP_PUBLICA.sslip.io tu-correo@example.com
```

Con dominio propio:

```bash
sudo /opt/quiniela_predictor_mx/infra/scripts/setup_ssl.sh quiniela.tu-dominio.com tu-correo@example.com
```

Certbot configura renovacion automatica.

## Verificar URL final

En la VM:

## Publicar en Streamlit Community Cloud

Streamlit Community Cloud debe apuntar a:

```text
Repository: miguellponcej/QuinielaMx
Branch: main
Main file path: app/streamlit_app.py
Python version: 3.12
```

Antes de desplegar, configura los secretos desde `App settings > Secrets`.
Usa `.streamlit/secrets.example.toml` como plantilla y pega valores reales
solo en el panel privado de Streamlit Cloud. No subas `.env` ni
`.streamlit/secrets.toml` al repositorio.

Secretos minimos:

```toml
APP_ENV = "production"
PRIVATE_BY_DEFAULT = "true"
APP_SECRET_KEY = "secreto-largo"
SESSION_SECRET = "secreto-largo"
AUTHORIZED_EMAILS = "miguellponcej@gmail.com"
AUTH_PASSWORD_HASH = "pbkdf2_sha256$..."
SESSION_TTL_SECONDS = "28800"
ENABLE_IP_ALLOWLIST = "false"
LOG_LEVEL = "INFO"
ACTIVE_DRAWS_REFRESH_MINUTES = "60"
```

Para generar el hash de password:

```bash
python -c "from src.auth.auth_service import hash_password; print(hash_password('TU_PASSWORD'))"
```

Para usar momios estructurados en produccion, agrega al panel de secretos las
claves disponibles:

```toml
THE_ODDS_API_KEY = ""
ODDS_API_IO_KEY = ""
FOOTBALL_DATA_API_KEY = ""
API_FOOTBALL_KEY = ""
SPORTS_GAME_ODDS_API_KEY = ""
```

La app carga `.env` solo en local y `st.secrets` en Streamlit Cloud. En ambos
casos mantiene la regla privada por defecto: sin login autorizado no renderiza
Home, predicciones, historicos ni configuracion.

```bash
cd /opt/quiniela_predictor_mx
infra/scripts/get_public_url.sh
infra/scripts/check_status.sh
```

Validaciones esperadas:

- `curl http://localhost:8501/_stcore/health` devuelve `ok`.
- `curl http://127.0.0.1` responde desde Nginx.
- `/.env` y `/data/` devuelven 404/403.
- El puerto 8501 no se abre publicamente; solo escucha en `127.0.0.1`.
- La app pide login antes de mostrar Home.
- Solo `miguellponcej@gmail.com` esta autorizado por `AUTHORIZED_EMAILS`.

## Reiniciar la app

```bash
ssh quiniela@IP_PUBLICA
/opt/quiniela_predictor_mx/infra/scripts/restart_app.sh
```

## Ver logs

```bash
ssh quiniela@IP_PUBLICA
cd /opt/quiniela_predictor_mx
docker compose logs -f --tail=100
sudo tail -f /var/log/nginx/quiniela_predictor_access.log
sudo tail -f /var/log/nginx/quiniela_predictor_error.log
tail -f data/security_logs/security_access.log
```

## Actualizar codigo

Desde tu maquina local:

```bash
infra/scripts/deploy_app.sh quiniela@IP_PUBLICA
```

## Backup

En la VM:

```bash
/opt/quiniela_predictor_mx/infra/scripts/backup_data.sh
```

El backup queda en `/opt/quiniela_predictor_mx/backups/` con permisos restrictivos.

## Detener la app

```bash
ssh quiniela@IP_PUBLICA
cd /opt/quiniela_predictor_mx
docker compose down
```

## Destruir infraestructura

Desde `infra/terraform`:

```bash
terraform destroy -var "digitalocean_token=${DIGITALOCEAN_TOKEN}"
```

## Seguridad aplicada

- App privada por defecto con `PRIVATE_BY_DEFAULT=true`.
- Lista blanca `AUTHORIZED_EMAILS=miguellponcej@gmail.com`.
- `.env`, `/data`, `/logs`, `/models`, `/cache`, backups y archivos ocultos bloqueados por Nginx.
- Streamlit solo en `127.0.0.1:8501`.
- UFW activo con 22, 80 y 443.
- Docker Compose con `restart: unless-stopped`.
- Logs de seguridad en `data/security_logs/security_access.log`.
- Home, predicciones, carga de archivos e historicos solo se renderizan despues de autenticacion.
