# Streamlit + GitHub + PayPal deployment

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
PAYPAL_MODE = "sandbox"
PAYPAL_CLIENT_ID = "your-paypal-client-id"
PAYPAL_CLIENT_SECRET = "your-paypal-client-secret"
OWNER_BTC_PUBLIC_ADDRESS = "your-public-btc-address"
```

Use `sandbox` first. Switch `PAYPAL_MODE` to `live` only after a successful test purchase.

`APP_BASE_URL` is only needed when you want to force a custom return URL. Otherwise, the app uses Streamlit's runtime URL as the PayPal return/cancel base.

After the app is deployed, open the **Setup** tab. It shows the same GitHub file URL,
the secrets template, the detected PayPal return URL, and a **Probar conexion PayPal**
button that validates the PayPal credentials without displaying them.

## PayPal setup

The app uses PayPal Orders API flow:

1. Create an order on the server side.
2. Send the buyer to PayPal approval.
3. Capture the order when the buyer returns.
4. Record the sale locally and unlock the PDF download.

Official PayPal Checkout guidance describes this backend flow: create an order, then capture the order after buyer approval. PayPal also recommends keeping `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` as environment variables/secrets.

## Security

- Do not paste PayPal secrets into chat.
- Do not commit `.streamlit/secrets.toml`.
- The app does not store cards, bank details, BTC private keys, seed phrases, or wallet passwords.
- BTC wallet support is display/reference only.
- Streamlit Community Cloud local storage can be ephemeral; for durable sales records, connect a managed database later.

## Local test

```bash
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

For local PayPal tests, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in sandbox credentials. Local tests default the PayPal return URL to `http://localhost:8501` when `APP_BASE_URL` is blank.

## Sources

- Streamlit deploy docs: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app
- Streamlit secrets docs: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management
- PayPal Checkout integration: https://developer.paypal.com/studio/checkout/standard/integrate
