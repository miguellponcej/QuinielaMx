# Streamlit Community Cloud

## Configuracion de la app

- Repository: `miguellponcej/QuinielaMx`
- Branch: `main`
- Main file path: `app/streamlit_app.py`
- Python version: `3.12`

## Secrets

Copia el contenido de `.streamlit/secrets.example.toml` al panel privado de
Streamlit Cloud en:

```text
App settings -> Secrets
```

No subas `.env` ni `.streamlit/secrets.toml`.

Minimo requerido:

```toml
APP_ENV = "production"
PRIVATE_BY_DEFAULT = "true"
APP_SECRET_KEY = "CAMBIAR"
SESSION_SECRET = "CAMBIAR"
AUTHORIZED_EMAILS = "miguellponcej@gmail.com"
AUTH_PASSWORD_HASH = "PEGAR_HASH_PBKDF2_SHA256"
SESSION_TTL_SECONDS = "28800"
ENABLE_IP_ALLOWLIST = "false"
LOG_LEVEL = "INFO"
ACTIVE_DRAWS_REFRESH_MINUTES = "60"
```

Generar hash de contrasena:

```bash
python -c "from src.auth.auth_service import hash_password; print(hash_password('TU_PASSWORD'))"
```

## Credenciales iniciales de la app

- Correo autorizado: `miguellponcej@gmail.com`
- Password local configurado previamente: `Julieta01$`

En Streamlit Cloud el password real depende del `AUTH_PASSWORD_HASH` que pegues
en Secrets.
