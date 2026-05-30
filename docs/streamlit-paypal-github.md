# Streamlit + GitHub + Stripe/PayPal deployment

This project now includes a Streamlit-native entrypoint:

```text
streamlit_app.py
```

It is separate from the existing Next.js app. Streamlit Community Cloud deploys Python apps from a GitHub repository, so this Streamlit entrypoint is the one to select in Streamlit.

## Files for Streamlit

- `streamlit_app.py` - main app.
- `requirements.txt` - Python dependencies Streamlit installs.
- `.streamlit/config.toml` - theme and server settings.
- `.streamlit/secrets.toml.example` - template only; never commit real secrets.
- `streamlit_src/stripe_checkout.py` - Stripe Checkout Session helpers.
- `streamlit_src/paypal.py` - PayPal order create/capture helpers.
- `streamlit_src/product_engine.py` - product, niche, landing, and marketing generation.
- `streamlit_src/pdf_delivery.py` - PDF export.

## Streamlit Cloud setup

1. Use the GitHub branch already pushed for this app:

```text
Repository: miguellponcej/QuinielaMx
Branch: ai-money-machine-streamlit
Main file path: streamlit_app.py
```

If Streamlit shows the "Paste GitHub URL" option, paste this exact file URL:

```text
https://github.com/miguellponcej/QuinielaMx/blob/ai-money-machine-streamlit/streamlit_app.py
```

2. Open Streamlit Community Cloud.
3. Create a new app from the GitHub repo.
4. Set the main file path to:

```text
streamlit_app.py
```

5. Add secrets in Streamlit app settings using the values below.

This branch was pushed without changing `QuinielaMx/main`. If you later create a dedicated empty repo under your account, run this from the project folder:

```powershell
.\scripts\push-to-github.ps1 -RepositoryUrl "https://github.com/miguellponcej/REPO_NAME.git"
```

Then deploy the repo in Streamlit Community Cloud.

Streamlit's official deployment docs state that Community Cloud deploys from your workspace/GitHub flow and installs dependencies from the app's dependency files. Streamlit's secrets docs also warn not to commit `secrets.toml`; use Streamlit app settings for secrets instead.

## Streamlit Secrets

Paste this into Streamlit Cloud > App > Settings > Secrets, replacing the values:

```toml
# Optional. If blank, the app detects its public Streamlit URL automatically.
APP_BASE_URL = ""
ADMIN_EMAIL = "owner@example.com"
ADMIN_PASSWORD = "replace-with-strong-owner-password"
ADMIN_PASSWORD_HASH = ""
OPENAI_API_KEY = ""
OPENAI_MODEL = "gpt-4.1-mini"
STRIPE_SECRET_KEY = "sk_test_replace_me"
PAYPAL_MODE = "sandbox"
PAYPAL_CLIENT_ID = "your-paypal-client-id"
PAYPAL_CLIENT_SECRET = "your-paypal-client-secret"
PAYPAL_PUBLIC_HANDLE = "miguellponcej"
OWNER_BTC_PUBLIC_ADDRESS = "your-public-btc-address"
RESEND_API_KEY = ""
EMAIL_FROM = "AI Digital Product Money Machine <onboarding@resend.dev>"
```

Use Stripe test mode first. For PayPal, use `sandbox` first and switch `PAYPAL_MODE` to `live` only after a successful test purchase.

`APP_BASE_URL` is only needed when you want to force a custom return URL. Otherwise, the app uses Streamlit's runtime URL as the Stripe and PayPal return/cancel base.
`OWNER_BTC_PUBLIC_ADDRESS` can be set here as a default or later from the private Admin panel.
`OPENAI_API_KEY` is optional. If it is blank, the app uses the local deterministic generator.

After the app is deployed, open the **Setup** tab. It shows the same GitHub file URL,
the secrets template, the detected return URL, and **Probar conexion Stripe** /
**Probar conexion PayPal** buttons that validate credentials without displaying them.

The deployed Streamlit app also includes:

- Owner login that keeps product generation, sales, wallet, reports, and admin views private.
- Optional OpenAI product generation with local fallback and safety filters.
- Public buyer storefront for checkout and paid download links.
- Product draft/publish persistence in local SQLite.
- Validated JSON product editor and public landing links per product from Admin.
- Editable JSON product version history with restore/publish actions from Admin.
- Stripe Checkout as the primary payment flow.
- Unique expiring download links after Stripe verification or PayPal capture.
- Basic receipt download after payment confirmation.
- Optional confirmation email through Resend when `RESEND_API_KEY` and `EMAIL_FROM` are configured.
- Sales dashboard with gross revenue, estimated net revenue, BTC equivalent, checkout conversion by landing/product, customers, pending payments, completed payments, CSV export, and financial JSON export.
- Wallet BTC tab with public address, accumulated revenue, BTC estimate, and manual conversion guidance.
- Admin tab for product price updates, customer export, delete actions, pending orders, and audit logs.
- Manual verified payment registration from Admin for PayPal public-handle payments.
- Manual verified Bitcoin payment preparation through the configured public BTC address.
- Editable public BTC address and commercial guarantee from Admin.
- Marketing tab with social/email/WhatsApp copy, A/B headline/CTA variants, and a simple content calendar.
- Optional PayPal public handle fallback (`PAYPAL_PUBLIC_HANDLE`) for manual payments while API credentials are pending. Manual payments do not unlock automatic delivery.

## Stripe setup

The app uses Stripe Checkout Sessions for one-time digital product payments:

1. Create a server-side Checkout Session.
2. Send the buyer to Stripe-hosted checkout.
3. When the buyer returns, retrieve the Checkout Session from Stripe.
4. Release the PDF only if `payment_status` is `paid`.

Keep `STRIPE_SECRET_KEY` in Streamlit Secrets. Do not paste it into chat or commit it.

## Owner login

Set `ADMIN_EMAIL` and a strong `ADMIN_PASSWORD` in Streamlit Secrets. The app keeps
the public landing/checkout visible, but hides product generation, financial dashboard,
wallet view, and admin tools until the owner logs in.

`ADMIN_PASSWORD_HASH` is optional. If you set it, use the SHA-256 hash of the password
and leave `ADMIN_PASSWORD` blank. Do not commit either value.

## PayPal setup

The app uses PayPal Orders API flow:

1. Create an order on the server side.
2. Send the buyer to PayPal approval.
3. Capture the order when the buyer returns.
4. Record the sale locally and unlock the PDF download.

Official PayPal Checkout guidance describes this backend flow: create an order, then capture the order after buyer approval. PayPal also recommends keeping `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` as environment variables/secrets.

## Bitcoin payment preparation

The app can show a public BTC address on the buyer landing page. BTC payments are manual:
the app does not monitor the chain, does not move funds, and does not unlock products
until the owner verifies the transaction and records it in Admin.

## Security

- Do not paste Stripe or PayPal secrets into chat.
- Do not paste the owner password into chat.
- Do not commit `.streamlit/secrets.toml`.
- The app does not store cards, bank details, BTC private keys, seed phrases, or wallet passwords.
- BTC wallet support is display/reference only.
- Streamlit Community Cloud local storage can be ephemeral; for durable sales records, connect a managed database later.

## Local test

```bash
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

For local payment tests, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in Stripe test and PayPal sandbox credentials. Local tests default the return URL to `http://localhost:8501` when `APP_BASE_URL` is blank.

## Sources

- Streamlit deploy docs: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app
- Streamlit secrets docs: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management
- OpenAI Responses API: https://platform.openai.com/docs/api-reference/responses/create
- OpenAI Structured Outputs: https://platform.openai.com/docs/guides/structured-outputs
- Stripe Checkout Sessions API: https://docs.stripe.com/api/checkout/sessions
- PayPal Checkout integration: https://developer.paypal.com/studio/checkout/standard/integrate
