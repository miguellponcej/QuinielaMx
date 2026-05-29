# AI Digital Product Money Machine

Herramienta web para crear, publicar, vender y entregar productos digitales reales. Incluye generador de nichos/productos, landing pages, checkout Stripe, entrega automatica por link con expiracion, dashboard financiero, CSV, email y wallet publica BTC para referencia de conversion.

La app esta disenada para ventas legitimas. No crea dinero de la nada, no hace phishing, no guarda tarjetas, no solicita seed phrases/private keys y no ejecuta transferencias BTC automaticas.

## Stack

- Next.js + TypeScript
- Tailwind CSS
- Prisma + PostgreSQL
- Stripe Checkout Sessions
- Streamlit deploy target with PayPal Checkout REST flow
- Resend via API HTTP
- PDF generado en servidor
- API BTC/USD de CoinGecko con fallback
- Auth propia con cookie firmada httpOnly

## Instalacion

```bash
npm install
cp .env.example .env
npm run db:generate
npm run db:push
npm run db:seed
npm run dev
```

Abre `http://localhost:3000`. El usuario admin se configura con `ADMIN_EMAIL` y `ADMIN_PASSWORD`.

## Variables de entorno

`APP_SECRET` debe ser un valor largo y aleatorio en produccion. `DATABASE_URL` debe apuntar a PostgreSQL. `STRIPE_SECRET_KEY` y `STRIPE_WEBHOOK_SECRET` activan pagos reales. `RESEND_API_KEY` activa el correo de entrega.

La app funciona en modo demo si faltan Stripe/Postgres/Resend, pero los pagos reales y persistencia requieren esas variables.

## Streamlit + PayPal

Tambien existe una version deployable en Streamlit:

```bash
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

Para Streamlit Community Cloud, usa:

```text
Repository: miguellponcej/QuinielaMx
Branch: ai-money-machine-streamlit
Main file path: streamlit_app.py
```

Tambien puedes usar "Paste GitHub URL" en Streamlit con:

```text
https://github.com/miguellponcej/QuinielaMx/blob/ai-money-machine-streamlit/streamlit_app.py
```

Configura `PAYPAL_MODE`, `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET` y `OWNER_BTC_PUBLIC_ADDRESS` en Streamlit Secrets, no en el repositorio. `APP_BASE_URL` es opcional; si queda vacio, la app detecta la URL publica de Streamlit para el retorno de PayPal.

Despues del deploy, abre la pestana `Setup` dentro de la app para validar que PayPal, la URL de retorno y la wallet publica quedaron configuradas.

Detalles completos: `docs/streamlit-paypal-github.md`.

## Stripe

La integracion usa Checkout Sessions para pagos de una sola vez. No se almacenan tarjetas ni datos bancarios sensibles. Configura el webhook de Stripe hacia:

```text
https://tu-dominio.com/api/stripe/webhook
```

Evento requerido:

```text
checkout.session.completed
```

Al confirmarse el pago, el webhook marca la orden como entregada, crea un `DownloadLink` unico con expiracion y envia el correo al comprador si Resend esta configurado.

## Bitcoin

El modulo BTC solo guarda una direccion publica para referencia. Calcula equivalente aproximado en BTC usando BTC/USD. No solicita, guarda ni procesa private keys, seed phrases, contrasenas ni retiros automaticos.

## Modelo de datos

Prisma incluye:

- `User`
- `Product`
- `ProductVersion`
- `LandingPage`
- `Customer`
- `Order`
- `Payment`
- `DownloadLink`
- `WalletConfig`
- `MarketingAsset`
- `AuditLog`

## Pruebas

```bash
npm run test
npm run typecheck
npm run build
```

Las pruebas cubren generacion responsable, validacion de wallet publica BTC, estimacion BTC/USD y reglas de acceso de links de descarga.

## Despliegue en Vercel

1. Crea un proyecto en Vercel conectado a este repositorio.
2. Configura `DATABASE_URL`, `APP_SECRET`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `NEXT_PUBLIC_APP_URL`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `RESEND_API_KEY` y `EMAIL_FROM`.
3. Ejecuta `npm run db:push` contra la base de produccion antes del primer lanzamiento.
4. Configura el webhook de Stripe con la URL publica de Vercel.
5. Prueba con Stripe test mode antes de pasar a live mode.

## Despliegue en servidor propio

```bash
npm install
npm run db:generate
npm run db:push
npm run build
npm run start
```

Usa un reverse proxy con HTTPS y define todas las variables de entorno en el proceso del servidor.

## Flujo principal

1. Entra al dashboard.
2. Escribe un nicho y genera investigacion.
3. Elige una idea de producto.
4. Genera contenido, landing y assets de marketing.
5. Exporta PDF y guarda version editable.
6. Publica la landing.
7. El comprador paga por Stripe Checkout.
8. El webhook confirma el pago.
9. Se crea un link unico de descarga y se envia email.
10. El dashboard registra ventas, ingresos, clientes, pendientes y conversion.
11. El panel BTC muestra el equivalente estimado hacia tu wallet publica.
