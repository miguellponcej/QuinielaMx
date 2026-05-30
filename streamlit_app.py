from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets as token_secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import pandas as pd
import requests
import streamlit as st

from streamlit_src.paypal import PayPalConfig, capture_order, create_order, paypal_access_token
from streamlit_src.pdf_delivery import product_pdf_bytes
from streamlit_src.product_engine import analyze_niche, generate_product, marketing_assets, product_from_dict
from streamlit_src.stripe_checkout import (
    StripeConfig,
    create_checkout_session,
    retrieve_checkout_session,
    stripe_account,
)


APP_NAME = "AI Digital Product Money Machine"
DB_PATH = Path("data/streamlit_sales.db")
DEPLOY_FILE_URL = (
    "https://github.com/miguellponcej/QuinielaMx/blob/"
    "ai-money-machine-streamlit/streamlit_app.py"
)
GITHUB_BRANCH_URL = "https://github.com/miguellponcej/QuinielaMx/tree/ai-money-machine-streamlit"
SECRETS_TEMPLATE = """APP_BASE_URL = ""
ADMIN_EMAIL = "owner@example.com"
ADMIN_PASSWORD = "replace-with-strong-owner-password"
ADMIN_PASSWORD_HASH = ""
STRIPE_SECRET_KEY = "sk_test_replace_me"
PAYPAL_MODE = "sandbox"
PAYPAL_CLIENT_ID = "your-paypal-client-id"
PAYPAL_CLIENT_SECRET = "your-paypal-client-secret"
PAYPAL_PUBLIC_HANDLE = "miguellponcej"
OWNER_BTC_PUBLIC_ADDRESS = "your-public-btc-address"
RESEND_API_KEY = ""
EMAIL_FROM = "AI Digital Product Money Machine <onboarding@resend.dev>"
"""


st.set_page_config(page_title=APP_NAME, page_icon="💼", layout="wide")


MAX_FAILED_LOGINS = 5
LOGIN_LOCK_MINUTES = 15


def secret(name: str, default: str = "") -> str:
    env_value = os.environ.get(name)
    try:
        value = st.secrets.get(name)
    except Exception:
        value = None
    if value is None or str(value).strip() == "":
        value = env_value
    return str(value) if value is not None else default


def app_base_url() -> str:
    configured_url = secret("APP_BASE_URL")
    if configured_url:
        return configured_url.rstrip("/")

    try:
        current_url = str(st.context.url or "")
    except Exception:
        current_url = ""

    if current_url:
        parsed = urlsplit(current_url)
        if parsed.scheme and parsed.netloc:
            path = parsed.path.rstrip("/")
            return urlunsplit((parsed.scheme, parsed.netloc, path, "", "")).rstrip("/")

    return "http://localhost:8501"


def is_placeholder(value: str) -> bool:
    cleaned = value.strip().lower()
    return cleaned == "" or cleaned.startswith(("replace", "your-")) or "replace-with" in cleaned


def owner_email() -> str:
    return secret("ADMIN_EMAIL", "owner@example.com").strip().lower()


def password_digest(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def owner_auth_configured() -> bool:
    password = secret("ADMIN_PASSWORD")
    password_hash = secret("ADMIN_PASSWORD_HASH")
    return not is_placeholder(password) or not is_placeholder(password_hash)


def verify_owner_credentials(email: str, password: str) -> bool:
    if email.strip().lower() != owner_email():
        return False

    configured_hash = secret("ADMIN_PASSWORD_HASH").strip()
    if not is_placeholder(configured_hash):
        return hmac.compare_digest(password_digest(password), configured_hash)

    configured_password = secret("ADMIN_PASSWORD").strip()
    if not is_placeholder(configured_password):
        return hmac.compare_digest(password, configured_password)

    return False


def owner_authenticated() -> bool:
    return bool(st.session_state.get("owner_authenticated", False))


def login_locked_until() -> datetime | None:
    raw_value = st.session_state.get("owner_login_locked_until")
    if not raw_value:
        return None
    try:
        locked_until = datetime.fromisoformat(str(raw_value))
    except ValueError:
        return None
    if locked_until <= datetime.now(timezone.utc):
        st.session_state.pop("owner_login_locked_until", None)
        st.session_state["owner_failed_logins"] = 0
        return None
    return locked_until


def register_failed_login(email: str) -> None:
    failed = int(st.session_state.get("owner_failed_logins", 0)) + 1
    st.session_state["owner_failed_logins"] = failed
    if failed >= MAX_FAILED_LOGINS:
        locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOGIN_LOCK_MINUTES)
        st.session_state["owner_login_locked_until"] = locked_until.isoformat()
    log_event("login_failed", "owner_session", email.strip().lower(), {"failed_attempts": failed})


def register_successful_login(email: str) -> None:
    st.session_state["owner_authenticated"] = True
    st.session_state["owner_email"] = email.strip().lower()
    st.session_state["owner_failed_logins"] = 0
    st.session_state.pop("owner_login_locked_until", None)
    log_event("login_success", "owner_session", email.strip().lower())


def logout_owner() -> None:
    email = str(st.session_state.get("owner_email", ""))
    st.session_state["owner_authenticated"] = False
    st.session_state.pop("owner_email", None)
    log_event("logout", "owner_session", email)


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            create table if not exists products (
                slug text primary key,
                title text not null,
                niche text not null,
                product_type text not null,
                price_usd real not null,
                status text not null default 'draft',
                product_json text not null,
                created_at text not null,
                updated_at text not null
            )
            """
        )
        conn.execute(
            """
            create table if not exists product_versions (
                id integer primary key autoincrement,
                product_slug text not null,
                version_number integer not null,
                status text not null,
                product_json text not null,
                created_at text not null,
                unique(product_slug, version_number)
            )
            """
        )
        conn.execute(
            """
            create table if not exists sales (
                id integer primary key autoincrement,
                paypal_order_id text unique,
                product_slug text not null,
                product_title text not null,
                customer_email text,
                amount_usd real not null,
                status text not null,
                captured_at text not null,
                raw_payload text
            )
            """
        )
        conn.execute(
            """
            create table if not exists pending_orders (
                paypal_order_id text primary key,
                product_slug text not null,
                product_json text not null,
                created_at text not null
            )
            """
        )
        conn.execute(
            """
            create table if not exists pending_stripe_sessions (
                stripe_session_id text primary key,
                product_slug text not null,
                product_json text not null,
                created_at text not null
            )
            """
        )
        conn.execute(
            """
            create table if not exists download_links (
                token text primary key,
                paypal_order_id text not null,
                product_slug text not null,
                product_json text not null,
                expires_at text not null,
                max_downloads integer not null default 3,
                download_count integer not null default 0,
                created_at text not null
            )
            """
        )
        conn.execute(
            """
            create table if not exists audit_logs (
                id integer primary key autoincrement,
                action text not null,
                entity text not null,
                entity_id text,
                metadata text,
                created_at text not null
            )
            """
        )
        conn.execute(
            """
            create table if not exists app_settings (
                key text primary key,
                value text not null,
                updated_at text not null
            )
            """
        )


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_event(action: str, entity: str, entity_id: str | None = None, metadata: dict[str, Any] | None = None) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            insert into audit_logs (action, entity, entity_id, metadata, created_at)
            values (?, ?, ?, ?, ?)
            """,
            (action, entity, entity_id, json.dumps(metadata or {}, ensure_ascii=False), now_utc()),
        )


def setting_value(key: str, default: str = "") -> str:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("select value from app_settings where key = ?", (key,)).fetchone()
    if not row:
        return default
    return str(row[0])


def save_setting(key: str, value: str) -> None:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            insert into app_settings (key, value, updated_at)
            values (?, ?, ?)
            on conflict(key) do update set
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, value.strip(), now_utc()),
        )
    log_event("save", "app_setting", key, {"value_length": len(value.strip())})


def wallet_public_address() -> str:
    return setting_value("owner_btc_public_address", secret("OWNER_BTC_PUBLIC_ADDRESS", "")).strip()


def commercial_guarantee() -> str:
    return setting_value(
        "commercial_guarantee",
        "Si el archivo no se puede descargar, se repone el link o se devuelve el pago segun revision.",
    ).strip()


def save_product(product: dict[str, Any], status: str = "draft") -> None:
    init_db()
    timestamp = now_utc()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            insert into products (
                slug, title, niche, product_type, price_usd, status,
                product_json, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(slug) do update set
                title = excluded.title,
                niche = excluded.niche,
                product_type = excluded.product_type,
                price_usd = excluded.price_usd,
                status = excluded.status,
                product_json = excluded.product_json,
                updated_at = excluded.updated_at
            """,
            (
                product["slug"],
                product["title"],
                product["niche"],
                product["product_type"],
                float(product["price_usd"]),
                status,
                json.dumps(product, ensure_ascii=False),
                timestamp,
                timestamp,
            ),
        )
        row = conn.execute(
            "select coalesce(max(version_number), 0) + 1 from product_versions where product_slug = ?",
            (product["slug"],),
        ).fetchone()
        version_number = int(row[0] if row else 1)
        conn.execute(
            """
            insert into product_versions (
                product_slug, version_number, status, product_json, created_at
            ) values (?, ?, ?, ?, ?)
            """,
            (
                product["slug"],
                version_number,
                status,
                json.dumps(product, ensure_ascii=False),
                timestamp,
            ),
        )
    log_event("save", "product", product["slug"], {"status": status, "version_number": version_number})


def products_frame() -> pd.DataFrame:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(
            "select slug, title, niche, product_type, price_usd, status, updated_at from products order by updated_at desc",
            conn,
        )


def published_products_frame() -> pd.DataFrame:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(
            """
            select slug, title, niche, product_type, price_usd, status, updated_at
            from products
            where status = 'published'
            order by updated_at desc
            """,
            conn,
        )


def saved_product(slug: str) -> dict[str, Any] | None:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("select product_json from products where slug = ?", (slug,)).fetchone()
    return json.loads(row[0]) if row else None


def product_versions_frame(slug: str) -> pd.DataFrame:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(
            """
            select id, product_slug, version_number, status, created_at
            from product_versions
            where product_slug = ?
            order by version_number desc
            """,
            conn,
            params=(slug,),
        )


def saved_product_version(version_id: int) -> dict[str, Any] | None:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "select product_json from product_versions where id = ?",
            (int(version_id),),
        ).fetchone()
    return json.loads(row[0]) if row else None


def delete_product(slug: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("delete from products where slug = ?", (slug,))
        conn.execute("delete from product_versions where product_slug = ?", (slug,))
    log_event("delete", "product", slug)


def record_pending_order(order_id: str, product: dict[str, Any]) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            insert or replace into pending_orders (
                paypal_order_id, product_slug, product_json, created_at
            ) values (?, ?, ?, ?)
            """,
            (
                order_id,
                product["slug"],
                json.dumps(product, ensure_ascii=False),
                now_utc(),
            ),
        )
    log_event("create", "pending_order", order_id, {"product_slug": product["slug"]})


def pending_product_for_order(order_id: str) -> dict[str, Any] | None:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "select product_json from pending_orders where paypal_order_id = ?",
            (order_id,),
        ).fetchone()
    if not row:
        return None
    return json.loads(row[0])


def record_pending_stripe_session(session_id: str, product: dict[str, Any]) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            insert or replace into pending_stripe_sessions (
                stripe_session_id, product_slug, product_json, created_at
            ) values (?, ?, ?, ?)
            """,
            (
                session_id,
                product["slug"],
                json.dumps(product, ensure_ascii=False),
                now_utc(),
            ),
        )
    log_event("create", "pending_stripe_session", session_id, {"product_slug": product["slug"]})


def pending_product_for_stripe_session(session_id: str) -> dict[str, Any] | None:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "select product_json from pending_stripe_sessions where stripe_session_id = ?",
            (session_id,),
        ).fetchone()
    if not row:
        return None
    return json.loads(row[0])


def customer_email_from_payload(capture_payload: dict[str, Any]) -> str:
    payer = capture_payload.get("payer", {})
    if payer.get("email_address"):
        return str(payer.get("email_address", "")).strip()
    customer_details = capture_payload.get("customer_details", {})
    if customer_details.get("email"):
        return str(customer_details.get("email", "")).strip()
    return str(capture_payload.get("customer_email", "")).strip()


def record_sale(order_id: str, product: dict[str, Any], capture_payload: dict[str, Any]) -> None:
    email = customer_email_from_payload(capture_payload)
    status = str(capture_payload.get("payment_status") or capture_payload.get("status", "CAPTURED")).upper()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            insert or ignore into sales (
                paypal_order_id, product_slug, product_title, customer_email,
                amount_usd, status, captured_at, raw_payload
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                product["slug"],
                product["title"],
                email,
                float(product["price_usd"]),
                status,
                now_utc(),
                json.dumps(capture_payload, ensure_ascii=False),
            ),
        )
    log_event("capture", "payment", order_id, {"product_slug": product["slug"]})


def confirm_manual_payment(
    order_id: str,
    product: dict[str, Any],
    customer_email: str,
    config: PayPalConfig,
    provider: str = "manual",
) -> tuple[str, str, bool]:
    payload = {
        "status": "MANUAL_CONFIRMED",
        "provider": provider,
        "payer": {"email_address": customer_email},
        "verified_by": "admin",
    }
    record_sale(order_id, product, payload)
    download_token, expires_at = ensure_download_link(order_id, product)
    download_url = f"{config.app_base_url}?download_token={download_token}"
    email_sent = send_delivery_email(customer_email, product, download_url, order_id)
    log_event("confirm", "manual_payment", order_id, {"product_slug": product["slug"], "email_sent": email_sent})
    return download_url, expires_at, email_sent


def create_download_link(order_id: str, product: dict[str, Any]) -> tuple[str, str]:
    token = token_secrets.token_urlsafe(24)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=48)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            insert into download_links (
                token, paypal_order_id, product_slug, product_json, expires_at,
                max_downloads, download_count, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                token,
                order_id,
                product["slug"],
                json.dumps(product, ensure_ascii=False),
                expires_at.isoformat(),
                3,
                0,
                now_utc(),
            ),
        )
    log_event("create", "download_link", token, {"order_id": order_id, "product_slug": product["slug"]})
    return token, expires_at.isoformat()


def download_link_for_order(order_id: str) -> tuple[str, str] | None:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            select token, expires_at
            from download_links
            where paypal_order_id = ?
            order by created_at desc
            limit 1
            """,
            (order_id,),
        ).fetchone()
    if not row:
        return None
    return str(row[0]), str(row[1])


def ensure_download_link(order_id: str, product: dict[str, Any]) -> tuple[str, str]:
    existing = download_link_for_order(order_id)
    if existing:
        return existing
    return create_download_link(order_id, product)


def product_for_download_token(token: str) -> tuple[dict[str, Any] | None, str | None]:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            select product_json, expires_at, download_count, max_downloads
            from download_links
            where token = ?
            """,
            (token,),
        ).fetchone()
        if not row:
            return None, "Link de descarga no encontrado."
        product_json, expires_at, download_count, max_downloads = row
        if datetime.fromisoformat(expires_at) <= datetime.now(timezone.utc):
            return None, "Link de descarga expirado."
        if int(download_count) >= int(max_downloads):
            return None, "Link de descarga agotado."
    return json.loads(product_json), None


def record_download_token(token: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "update download_links set download_count = download_count + 1 where token = ?",
            (token,),
        )
    log_event("download", "download_link", token)


def receipt_text(order_id: str, product: dict[str, Any]) -> str:
    payment_label = "Sesion Stripe" if order_id.startswith("stripe_") else "Pago verificado"
    return "\n".join(
        [
            APP_NAME,
            "Recibo basico",
            f"{payment_label}: {order_id}",
            f"Producto: {product['title']}",
            f"Monto: ${float(product['price_usd']):.2f} USD",
            f"Fecha UTC: {now_utc()}",
            "Entrega: producto digital descargable.",
        ]
    )


def payer_email(capture_payload: dict[str, Any]) -> str:
    return customer_email_from_payload(capture_payload)


def send_delivery_email(customer_email: str, product: dict[str, Any], download_url: str, order_id: str) -> bool:
    api_key = secret("RESEND_API_KEY")
    email_from = secret("EMAIL_FROM", "AI Digital Product Money Machine <onboarding@resend.dev>")
    if not api_key or not customer_email:
        log_event("skip", "email", order_id, {"reason": "missing_email_config_or_customer"})
        return False

    payload = {
        "from": email_from,
        "to": [customer_email],
        "subject": f"Tu descarga: {product['title']}",
        "text": "\n".join(
            [
                "Gracias por tu compra.",
                f"Producto: {product['title']}",
                f"Pago: {order_id}",
                f"Descarga: {download_url}",
                "El link expira en 48 horas o despues de 3 descargas.",
                "",
                receipt_text(order_id, product),
            ]
        ),
    }
    response = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=20,
    )
    response.raise_for_status()
    log_event("send", "email", order_id, {"to": customer_email})
    return True


def sales_frame() -> pd.DataFrame:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query("select * from sales order by captured_at desc", conn)


def pending_orders_frame() -> pd.DataFrame:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query("select * from pending_orders order by created_at desc", conn)


def pending_stripe_sessions_frame() -> pd.DataFrame:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query("select * from pending_stripe_sessions order by created_at desc", conn)


def pending_payments_frame() -> pd.DataFrame:
    paypal_df = pending_orders_frame()
    stripe_df = pending_stripe_sessions_frame()
    frames = []
    if not paypal_df.empty:
        paypal_view = paypal_df.rename(columns={"paypal_order_id": "payment_id"}).copy()
        paypal_view["provider"] = "paypal"
        frames.append(paypal_view[["provider", "payment_id", "product_slug", "created_at"]])
    if not stripe_df.empty:
        stripe_view = stripe_df.rename(columns={"stripe_session_id": "payment_id"}).copy()
        stripe_view["provider"] = "stripe"
        frames.append(stripe_view[["provider", "payment_id", "product_slug", "created_at"]])
    if not frames:
        return pd.DataFrame(columns=["provider", "payment_id", "product_slug", "created_at"])
    return pd.concat(frames, ignore_index=True).sort_values("created_at", ascending=False)


def audit_frame() -> pd.DataFrame:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query("select * from audit_logs order by created_at desc limit 100", conn)


def revenue_summary() -> dict[str, float | int]:
    df = sales_frame()
    pending_df = pending_payments_frame()
    gross = float(df["amount_usd"].sum()) if not df.empty else 0.0
    completed = int(len(df))
    pending = int(len(pending_df))
    attempts = completed + pending
    conversion = (completed / attempts * 100.0) if attempts else 0.0
    net_estimate = max(gross - (gross * 0.0349) - (completed * 0.49), 0.0) if gross else 0.0
    return {
        "gross": gross,
        "net_estimate": net_estimate,
        "completed": completed,
        "pending": pending,
        "conversion": conversion,
    }


def btc_rate_usd() -> float:
    try:
        response = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
            timeout=10,
        )
        response.raise_for_status()
        return float(response.json()["bitcoin"]["usd"])
    except Exception:
        return 68000.0


def paypal_config() -> PayPalConfig:
    return PayPalConfig(
        mode=secret("PAYPAL_MODE", "sandbox").lower(),
        client_id=secret("PAYPAL_CLIENT_ID"),
        client_secret=secret("PAYPAL_CLIENT_SECRET"),
        app_base_url=app_base_url(),
    )


def stripe_config() -> StripeConfig:
    return StripeConfig(
        secret_key=secret("STRIPE_SECRET_KEY"),
        app_base_url=app_base_url(),
    )


def paypal_public_handle() -> str:
    handle = secret("PAYPAL_PUBLIC_HANDLE", "miguellponcej").strip()
    return handle.lstrip("@")


def render_security_notice() -> None:
    st.info(
        "Venta legitima: Stripe o PayPal procesan el pago. Esta app no guarda tarjetas, cuentas bancarias, "
        "seed phrases, private keys ni contrasenas de wallet."
    )


def missing_setup_items(paypal: PayPalConfig, stripe: StripeConfig, btc_address: str) -> list[str]:
    missing = []
    if not stripe.is_configured:
        missing.append("STRIPE_SECRET_KEY")
    if not paypal.client_id.strip() or paypal.client_id.startswith(("replace", "your-")):
        missing.append("PAYPAL_CLIENT_ID para respaldo PayPal")
    if not paypal.client_secret.strip() or paypal.client_secret.startswith(("replace", "your-")):
        missing.append("PAYPAL_CLIENT_SECRET para respaldo PayPal")
    if paypal.mode not in {"sandbox", "live"}:
        missing.append("PAYPAL_MODE debe ser sandbox o live")
    if not btc_address.strip() or btc_address.startswith(("replace", "your-")):
        missing.append("OWNER_BTC_PUBLIC_ADDRESS")
    return missing


def render_setup_tab(paypal: PayPalConfig, stripe: StripeConfig, btc_address: str, public_paypal_handle: str) -> None:
    st.subheader("Setup de Streamlit, GitHub, Stripe y PayPal")
    st.write("Usa estos datos para levantar la app en Streamlit Cloud desde tu GitHub.")
    col_a, col_b = st.columns(2)
    col_a.link_button("Abrir archivo para Streamlit", DEPLOY_FILE_URL, width="stretch")
    col_b.link_button("Abrir rama en GitHub", GITHUB_BRANCH_URL, width="stretch")
    st.code(DEPLOY_FILE_URL, language="text")

    st.write("Pega esta plantilla en Streamlit Cloud > App > Settings > Secrets.")
    st.code(SECRETS_TEMPLATE, language="toml")
    st.caption("APP_BASE_URL puede quedar vacio; la app detecta su URL publica para retornos de Stripe y PayPal.")

    missing = missing_setup_items(paypal, stripe, btc_address)
    if missing:
        st.warning("Configuracion pendiente: " + ", ".join(missing))
    else:
        st.success("Los secretos basicos estan presentes.")

    st.write("Estado detectado")
    status_col_1, status_col_2, status_col_3, status_col_4, status_col_5, status_col_6 = st.columns(6)
    status_col_1.metric("Stripe", "listo" if stripe.is_configured else "pendiente")
    status_col_2.metric("PayPal", "listo" if paypal.is_configured else "pendiente")
    status_col_3.metric("Modo PayPal", paypal.mode)
    status_col_4.metric("Wallet BTC", "lista" if btc_address.strip() else "pendiente")
    status_col_5.metric("PayPal publico", f"@{public_paypal_handle}" if public_paypal_handle else "pendiente")
    status_col_6.metric("Login dueno", "listo" if owner_auth_configured() else "pendiente")
    st.caption(f"URL de retorno detectada: {stripe.app_base_url}")

    if st.button("Probar conexion Stripe", width="stretch"):
        if not stripe.is_configured:
            st.error("Agrega STRIPE_SECRET_KEY en Streamlit Secrets antes de probar.")
        else:
            with st.spinner("Probando credenciales con Stripe..."):
                try:
                    account = stripe_account(stripe)
                    st.success(f"Stripe respondio correctamente. Cuenta: {account.get('id', 'activa')}")
                except Exception as exc:
                    st.error(f"Stripe no respondio con esas credenciales: {exc}")

    if st.button("Probar conexion PayPal", width="stretch"):
        if not paypal.is_configured:
            st.error("Agrega PAYPAL_CLIENT_ID y PAYPAL_CLIENT_SECRET en Streamlit Secrets antes de probar.")
        else:
            with st.spinner("Probando credenciales con PayPal..."):
                try:
                    paypal_access_token(paypal)
                    st.success("PayPal respondio correctamente. El checkout puede crear ordenes.")
                except Exception as exc:
                    st.error(f"PayPal no respondio con esas credenciales: {exc}")


def render_download_token_if_needed() -> bool:
    token = st.query_params.get("download_token")
    if not token:
        return False

    product, error = product_for_download_token(str(token))
    if error or not product:
        st.error(error or "No se pudo preparar la descarga.")
        return True

    st.success("Link valido. Tu producto digital esta listo.")
    st.download_button(
        "Descargar PDF",
        data=product_pdf_bytes(product_from_dict(product)),
        file_name=f"{product['slug']}.pdf",
        mime="application/pdf",
        on_click=record_download_token,
        args=(str(token),),
        width="stretch",
    )
    return True


def product_dict_from_product(product: Any) -> dict[str, Any]:
    product_dict = product.to_dict()
    product_dict["slug"] = product.slug
    return product_dict


def default_product_dict() -> dict[str, Any]:
    market = "consultores independientes"
    analysis = analyze_niche(market)
    product = generate_product(market, analysis["ideas"][0])
    return product_dict_from_product(product)


def public_product_choice(fallback_product: dict[str, Any]) -> dict[str, Any]:
    published_df = published_products_frame()
    if published_df.empty:
        return fallback_product

    requested_slug = str(st.query_params.get("product_slug", "")).strip()
    if requested_slug:
        requested_product = saved_product(requested_slug)
        if requested_product:
            return requested_product

    product_titles = {
        row["title"]: row["slug"]
        for _, row in published_df.iterrows()
    }
    selected_title = st.selectbox("Producto", list(product_titles.keys()), label_visibility="collapsed")
    return saved_product(product_titles[selected_title]) or fallback_product


def render_owner_login() -> None:
    if owner_authenticated():
        st.success(f"Sesion dueno activa: {st.session_state.get('owner_email', owner_email())}")
        if st.button("Cerrar sesion", width="stretch"):
            logout_owner()
            st.rerun()
        return

    st.subheader("Acceso dueno")
    if not owner_auth_configured():
        st.warning("Configura ADMIN_EMAIL y ADMIN_PASSWORD en Streamlit Secrets para abrir el panel privado.")
        return

    locked_until = login_locked_until()
    if locked_until:
        st.error(f"Login pausado hasta {locked_until.isoformat()} UTC por intentos fallidos.")
        return

    email = st.text_input("Email admin", value=owner_email(), key="owner_login_email")
    password = st.text_input("Password admin", type="password", key="owner_login_password")
    if st.button("Entrar al panel", type="primary", width="stretch"):
        if verify_owner_credentials(email, password):
            register_successful_login(email)
            st.rerun()
        else:
            register_failed_login(email)
            remaining = max(MAX_FAILED_LOGINS - int(st.session_state.get("owner_failed_logins", 0)), 0)
            st.error(f"Credenciales incorrectas. Intentos restantes: {remaining}.")


def render_landing_checkout(
    product_dict: dict[str, Any],
    stripe: StripeConfig,
    paypal: PayPalConfig,
    public_paypal_handle: str,
    key_prefix: str,
) -> None:
    product = product_from_dict(product_dict)
    st.subheader(product.title)
    st.write(product.subtitle)
    st.write("**Problema que resuelve**")
    st.write(
        f"Personas en {product.niche} necesitan una herramienta concreta para tomar accion sin promesas exageradas."
    )
    for bullet in product.sales_bullets:
        st.write(f"- {bullet}")
    st.write("**Que incluye**")
    for item in product.table_of_contents:
        st.write(f"- {item}")
    st.write("**Preguntas frecuentes**")
    st.write("- Es una herramienta practica, no una promesa de ingresos.")
    st.write("- La entrega se hace con un link unico despues de confirmar el pago.")
    st.write("- El link dura 48 horas o 3 descargas.")
    st.write("**Garantia comercial**")
    st.write(commercial_guarantee())
    st.divider()
    st.metric("Precio", f"${float(product_dict['price_usd']):.2f} USD")

    if stripe.is_configured:
        if st.button("Crear checkout Stripe", type="primary", width="stretch", key=f"{key_prefix}_stripe_checkout"):
            with st.spinner("Creando checkout Stripe..."):
                try:
                    session = create_checkout_session(stripe, product_dict)
                    record_pending_stripe_session(session["id"], product_dict)
                    st.session_state[f"{key_prefix}_last_stripe_session"] = session
                    st.success("Checkout creado. Abre Stripe para completar el pago.")
                except Exception as exc:
                    st.error(f"No se pudo crear el checkout Stripe: {exc}")
        stripe_session = st.session_state.get(f"{key_prefix}_last_stripe_session")
        if stripe_session:
            st.link_button("Pagar con Stripe", stripe_session["url"], width="stretch")
    else:
        st.warning("El checkout principal Stripe todavia no esta configurado.")

    st.divider()
    st.caption("PayPal queda disponible como respaldo o para pagos manuales verificados.")

    if paypal.is_configured:
        if st.button("Crear checkout PayPal", width="stretch", key=f"{key_prefix}_paypal_checkout"):
            with st.spinner("Creando orden PayPal..."):
                try:
                    order = create_order(paypal, product_dict)
                    record_pending_order(order["id"], product_dict)
                    st.session_state[f"{key_prefix}_last_paypal_order"] = order
                    st.success("Orden creada. Abre PayPal para completar el pago.")
                except Exception as exc:
                    st.error(f"No se pudo crear la orden PayPal: {exc}")
        order = st.session_state.get(f"{key_prefix}_last_paypal_order")
        if order:
            st.link_button("Pagar con PayPal", order["approval_url"], width="stretch")
    elif public_paypal_handle:
        st.link_button(
            f"Pago manual por PayPal @{public_paypal_handle}",
            f"https://www.paypal.me/{public_paypal_handle}",
            width="stretch",
        )
        st.caption(
            "Pago manual no confirma automaticamente la orden ni libera descarga. "
            "El dueno debe verificarlo en PayPal y generar entrega desde Admin."
        )

    btc_address = wallet_public_address()
    if btc_address:
        st.divider()
        st.write("**Pago manual en Bitcoin**")
        st.code(btc_address, language="text")
        st.caption(
            "Opcion preparada para pagos BTC manuales. No libera descargas automaticamente; "
            "el dueno debe verificar la transaccion antes de generar entrega."
        )

    st.info("Despues del retorno de Stripe o PayPal, la app verifica el pago y habilita la descarga del PDF.")


def render_public_storefront(
    fallback_product: dict[str, Any],
    stripe: StripeConfig,
    paypal: PayPalConfig,
    public_paypal_handle: str,
) -> None:
    st.header("Landing publica")
    st.caption("Vista para compradores. El panel privado requiere login del dueno.")
    product_dict = public_product_choice(fallback_product)
    render_landing_checkout(product_dict, stripe, paypal, public_paypal_handle, "public")


def capture_return_if_needed(product: dict[str, Any], config: PayPalConfig) -> bool:
    params = st.query_params
    token = params.get("token")
    returned = params.get("paypal_return")
    if not token or not returned:
        return False

    if not config.is_configured:
        st.error("PayPal no esta configurado en Streamlit Secrets; no se puede capturar el pago.")
        return False

    with st.spinner("Confirmando pago con PayPal..."):
        try:
            purchased_product = pending_product_for_order(str(token)) or product
            payload = capture_order(config, str(token))
            record_sale(str(token), purchased_product, payload)
            download_token, expires_at = ensure_download_link(str(token), purchased_product)
            download_url = f"{config.app_base_url}?download_token={download_token}"
            email_sent = send_delivery_email(payer_email(payload), purchased_product, download_url, str(token))
            st.success("Pago confirmado. Tu descarga esta lista.")
            st.code(download_url, language="text")
            st.caption(f"Link unico valido hasta {expires_at} UTC o 3 descargas.")
            if email_sent:
                st.info("Correo de confirmacion enviado al comprador.")
            else:
                st.info("Correo no enviado: configura RESEND_API_KEY y EMAIL_FROM para activar envio automatico.")
            st.download_button(
                "Descargar PDF comprado",
                data=product_pdf_bytes(product_from_dict(purchased_product)),
                file_name=f"{purchased_product['slug']}.pdf",
                mime="application/pdf",
                width="stretch",
            )
            st.download_button(
                "Descargar recibo",
                data=receipt_text(str(token), purchased_product),
                file_name=f"recibo-{purchased_product['slug']}.txt",
                mime="text/plain",
                width="stretch",
            )
            return True
        except Exception as exc:
            st.error(f"No se pudo capturar el pago de PayPal: {exc}")
            return False


def capture_stripe_return_if_needed(product: dict[str, Any], config: StripeConfig) -> bool:
    params = st.query_params
    session_id = params.get("session_id")
    returned = params.get("stripe_success")
    canceled = params.get("stripe_cancel")

    if canceled:
        st.warning("Checkout de Stripe cancelado. No se registro ningun pago.")
        return True
    if not session_id or not returned:
        return False

    if not config.is_configured:
        st.error("Stripe no esta configurado en Streamlit Secrets; no se puede verificar el pago.")
        return True

    with st.spinner("Verificando pago con Stripe..."):
        try:
            payload = retrieve_checkout_session(config, str(session_id))
            if str(payload.get("payment_status", "")).lower() != "paid":
                st.warning("Stripe aun no marca este pago como pagado. No se libero la descarga.")
                return True

            metadata = payload.get("metadata", {}) or {}
            purchased_product = (
                pending_product_for_stripe_session(str(session_id))
                or saved_product(str(metadata.get("product_slug", "")))
                or product
            )
            payment_id = f"stripe_{session_id}"
            record_sale(payment_id, purchased_product, {**payload, "provider": "stripe"})
            download_token, expires_at = ensure_download_link(payment_id, purchased_product)
            download_url = f"{config.app_base_url}?download_token={download_token}"
            email_sent = send_delivery_email(payer_email(payload), purchased_product, download_url, payment_id)
            st.success("Pago Stripe confirmado. Tu descarga esta lista.")
            st.code(download_url, language="text")
            st.caption(f"Link unico valido hasta {expires_at} UTC o 3 descargas.")
            if email_sent:
                st.info("Correo de confirmacion enviado al comprador.")
            else:
                st.info("Correo no enviado: configura RESEND_API_KEY y EMAIL_FROM para activar envio automatico.")
            st.download_button(
                "Descargar PDF comprado",
                data=product_pdf_bytes(product_from_dict(purchased_product)),
                file_name=f"{purchased_product['slug']}.pdf",
                mime="application/pdf",
                width="stretch",
            )
            st.download_button(
                "Descargar recibo",
                data=receipt_text(payment_id, purchased_product),
                file_name=f"recibo-{purchased_product['slug']}.txt",
                mime="text/plain",
                width="stretch",
            )
            return True
        except Exception as exc:
            st.error(f"No se pudo verificar el pago de Stripe: {exc}")
            return True


def main() -> None:
    init_db()
    paypal = paypal_config()
    stripe = stripe_config()
    public_paypal_handle = paypal_public_handle()
    btc_address = wallet_public_address()
    fallback_product = default_product_dict()

    st.title(APP_NAME)
    st.caption("Crea, publica, cobra con Stripe/PayPal y entrega productos digitales reales.")
    render_security_notice()
    if render_download_token_if_needed():
        st.stop()

    if capture_stripe_return_if_needed(fallback_product, stripe) or capture_return_if_needed(fallback_product, paypal):
        st.stop()

    with st.sidebar:
        st.header("Configuracion")
        st.write("Stripe:", "configurado" if stripe.is_configured else "pendiente")
        st.write("PayPal:", "configurado" if paypal.is_configured else "pendiente")
        st.write("Modo PayPal:", paypal.mode)
        st.write("PayPal publico:", f"@{public_paypal_handle}" if public_paypal_handle else "pendiente")
        st.caption(f"Retorno: {stripe.app_base_url}")
        st.text_input("Wallet BTC publica", value=btc_address, disabled=True)
        st.caption("Solo referencia publica. No se solicitan ni guardan llaves privadas.")
        st.divider()
        render_owner_login()

    if not owner_authenticated():
        render_public_storefront(fallback_product, stripe, paypal, public_paypal_handle)
        st.stop()

    tab_setup, tab_build, tab_landing, tab_sales, tab_wallet, tab_marketing, tab_admin = st.tabs(
        ["Setup", "Producto", "Landing y checkout", "Ventas", "Wallet BTC", "Marketing", "Admin"]
    )

    with tab_setup:
        render_setup_tab(paypal, stripe, btc_address, public_paypal_handle)

    with tab_build:
        col_left, col_right = st.columns([0.9, 1.1], gap="large")
        with col_left:
            market = st.text_input("Mercado objetivo", value="consultores independientes")
            analysis = analyze_niche(market)
            st.subheader("Cliente ideal")
            st.write(analysis["customer_profile"])
            st.subheader("Ideas rentables")
            idea_titles = [idea["title"] for idea in analysis["ideas"]]
            selected_title = st.radio("Elige una idea", idea_titles, label_visibility="collapsed")
            selected_idea = next(idea for idea in analysis["ideas"] if idea["title"] == selected_title)

        product = generate_product(market, selected_idea)
        product_dict = product_dict_from_product(product)

        with col_right:
            st.subheader(product.title)
            st.write(product.subtitle)
            st.metric("Precio sugerido", f"${product.price_usd:.2f} USD")
            st.write("**Indice**")
            for index, item in enumerate(product.table_of_contents, start=1):
                st.write(f"{index}. {item}")
            st.download_button(
                "Exportar PDF",
                data=product_pdf_bytes(product),
                file_name=f"{product.slug}.pdf",
                mime="application/pdf",
                width="stretch",
            )
            st.download_button(
                "Descargar version editable JSON",
                data=json.dumps(product_dict, indent=2, ensure_ascii=False),
                file_name=f"{product.slug}.json",
                mime="application/json",
                width="stretch",
            )
            col_save, col_publish = st.columns(2)
            if col_save.button("Guardar borrador", width="stretch"):
                save_product(product_dict, "draft")
                st.success("Producto guardado como borrador.")
            if col_publish.button("Publicar producto", type="primary", width="stretch"):
                save_product(product_dict, "published")
                st.success("Producto publicado en el catalogo local.")

    with tab_landing:
        capture_stripe_return_if_needed(product_dict, stripe)
        capture_return_if_needed(product_dict, paypal)
        st.subheader(product.title)
        st.write(product.subtitle)
        st.write("**Problema que resuelve**")
        st.write(
            f"Personas en {product.niche} necesitan una herramienta concreta para tomar accion sin promesas exageradas."
        )
        for bullet in product.sales_bullets:
            st.write(f"- {bullet}")
        st.write("**Que incluye**")
        for item in product.table_of_contents:
            st.write(f"- {item}")
        st.write("**Preguntas frecuentes**")
        st.write("- ¿Es una promesa de ingresos? No. Es una herramienta practica para ejecutar mejor.")
        st.write("- ¿Como se entrega? Despues del pago se genera un link unico de descarga.")
        st.write("- ¿Cuanto dura el acceso? 48 horas o 3 descargas por link.")
        st.write("**Garantia comercial**")
        st.write(commercial_guarantee())
        st.divider()
        st.metric("Precio", f"${product.price_usd:.2f} USD")

        if stripe.is_configured:
            if st.button("Crear checkout Stripe", type="primary", width="stretch"):
                with st.spinner("Creando checkout Stripe..."):
                    try:
                        session = create_checkout_session(stripe, product_dict)
                        record_pending_stripe_session(session["id"], product_dict)
                        st.session_state["last_stripe_session"] = session
                        st.success("Checkout creado. Abre Stripe para completar el pago.")
                    except Exception as exc:
                        st.error(f"No se pudo crear el checkout Stripe: {exc}")
            stripe_session = st.session_state.get("last_stripe_session")
            if stripe_session:
                st.link_button("Pagar con Stripe", stripe_session["url"], width="stretch")
        else:
            st.warning("Configura STRIPE_SECRET_KEY en Streamlit Secrets para activar el checkout principal.")

        st.divider()
        st.caption("PayPal queda disponible como respaldo o para pagos manuales verificados.")

        if paypal.is_configured:
            if st.button("Crear checkout PayPal", width="stretch"):
                with st.spinner("Creando orden PayPal..."):
                    try:
                        order = create_order(paypal, product_dict)
                        record_pending_order(order["id"], product_dict)
                        st.session_state["last_paypal_order"] = order
                        st.success("Orden creada. Abre PayPal para completar el pago.")
                    except Exception as exc:
                        st.error(f"No se pudo crear la orden PayPal: {exc}")
            order = st.session_state.get("last_paypal_order")
            if order:
                st.link_button("Pagar con PayPal", order["approval_url"], width="stretch")
        else:
            st.warning(
                "Configura PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET y PAYPAL_MODE "
                "en Streamlit Secrets para activar cobros reales."
            )
            if public_paypal_handle:
                st.link_button(
                    f"Pago manual por PayPal @{public_paypal_handle}",
                    f"https://www.paypal.me/{public_paypal_handle}",
                    width="stretch",
                )
                st.caption(
                    "Pago manual no confirma automaticamente la orden ni libera descarga. "
                    "Usalo solo mientras configuras credenciales API de PayPal."
                )

        st.info("Despues del retorno de Stripe o PayPal, la app verifica el pago y habilita la descarga del PDF.")

    with tab_sales:
        df = sales_frame()
        pending_df = pending_payments_frame()
        summary = revenue_summary()
        gross = float(summary["gross"])
        net_estimate = float(summary["net_estimate"])
        rate = btc_rate_usd()
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Ventas registradas", str(summary["completed"]))
        col2.metric("Ingresos brutos", f"${gross:.2f} USD")
        col3.metric("Neto estimado", f"${net_estimate:.2f} USD")
        col4.metric("Equivalente BTC", f"{(gross / rate if rate else 0):.8f}")
        col5.metric("Conversion checkout", f"{float(summary['conversion']):.1f}%")
        st.caption("Neto estimado usa una aproximacion de comisiones de pasarela; confirma cifras finales en Stripe/PayPal.")
        if not df.empty:
            best = df.groupby("product_title")["amount_usd"].agg(["count", "sum"]).reset_index()
            best = best.sort_values(["count", "sum"], ascending=False)
            st.subheader("Productos mas vendidos")
            st.dataframe(best, width="stretch", hide_index=True)
            st.metric("Clientes registrados", str(df["customer_email"].dropna().replace("", pd.NA).dropna().nunique()))
        st.metric("Pagos pendientes", str(len(pending_df)))
        st.metric("Pagos completados", str(len(df)))
        st.dataframe(df, width="stretch", hide_index=True)
        st.download_button(
            "Exportar ventas CSV",
            data=df.to_csv(index=False),
            file_name="sales-report.csv",
            mime="text/csv",
            width="stretch",
        )
        report_payload = {
            "generated_at": now_utc(),
            "gross_usd": gross,
            "net_estimate_usd": net_estimate,
            "btc_usd_rate": rate,
            "gross_btc_estimate": gross / rate if rate else 0,
            "completed_payments": summary["completed"],
            "pending_payments": summary["pending"],
            "checkout_conversion_percent": summary["conversion"],
        }
        st.download_button(
            "Exportar reporte financiero JSON",
            data=json.dumps(report_payload, indent=2),
            file_name="financial-report.json",
            mime="application/json",
            width="stretch",
        )

    with tab_wallet:
        summary = revenue_summary()
        gross = float(summary["gross"])
        net_estimate = float(summary["net_estimate"])
        rate = btc_rate_usd()
        btc_gross = gross / rate if rate else 0.0
        btc_net = net_estimate / rate if rate else 0.0
        st.subheader("Wallet publica de Bitcoin")
        st.text_input("Direccion publica BTC", value=btc_address, disabled=True)
        st.metric("Ingresos brutos acumulados", f"${gross:.2f} USD")
        st.metric("Equivalente bruto estimado", f"{btc_gross:.8f} BTC")
        st.metric("Equivalente neto estimado", f"{btc_net:.8f} BTC")
        st.caption(f"Tipo de cambio BTC/USD usado: ${rate:,.2f}. Es una estimacion, no una orden de conversion.")
        st.write("Sugerencia manual")
        if btc_address:
            st.write(
                "Cuando Stripe o PayPal liquiden tus fondos, puedes convertir manualmente parte del saldo a BTC "
                "en un exchange de tu eleccion y retirar a la direccion publica configurada."
            )
        else:
            st.warning("Configura OWNER_BTC_PUBLIC_ADDRESS en Streamlit Secrets para mostrar el destino publico.")
        st.info(
            "La app no mueve fondos, no hace trading automatico y nunca solicita private keys, seed phrases ni passwords."
        )

    with tab_marketing:
        st.subheader("Copies generados")
        for asset in marketing_assets(product):
            with st.expander(f"{asset['channel']} - {asset['kind']}"):
                st.write(asset["copy"])
        st.subheader("Variantes A/B")
        st.write(f"A: {product.title}")
        st.write(f"B: {product.product_type.title()} practico para {product.niche}")
        st.write("CTA A: Descargar guia ahora")
        st.write("CTA B: Ver el plan practico")
        st.subheader("Calendario basico")
        calendar_rows = [
            {"dia": 1, "canal": "Instagram", "pieza": "Problema principal + CTA"},
            {"dia": 2, "canal": "Email", "pieza": "Historia breve + beneficio"},
            {"dia": 3, "canal": "TikTok", "pieza": "Hook rapido + tip"},
            {"dia": 4, "canal": "WhatsApp", "pieza": "Mensaje directo con link"},
            {"dia": 5, "canal": "Google", "pieza": "Anuncio de busqueda"},
        ]
        st.dataframe(pd.DataFrame(calendar_rows), width="stretch", hide_index=True)

    with tab_admin:
        st.subheader("Panel administrativo")
        st.write("Metodos de pago")
        st.write("Stripe Checkout:", "configurado" if stripe.is_configured else "pendiente")
        st.write("PayPal API:", "configurado" if paypal.is_configured else "pendiente")
        st.write("PayPal publico:", f"@{public_paypal_handle}" if public_paypal_handle else "pendiente")
        st.write("Bitcoin:", "direccion publica configurada" if btc_address else "pendiente")
        with st.expander("Configuracion publica"):
            updated_btc_address = st.text_input(
                "Direccion publica BTC",
                value=btc_address,
                key="admin_btc_public_address",
                help="Solo direccion publica. Nunca ingreses private keys, seed phrases ni passwords.",
            )
            updated_guarantee = st.text_area(
                "Garantia comercial",
                value=commercial_guarantee(),
                key="admin_commercial_guarantee",
            )
            if st.button("Guardar configuracion publica", width="stretch"):
                save_setting("owner_btc_public_address", updated_btc_address)
                save_setting("commercial_guarantee", updated_guarantee)
                st.success("Configuracion publica actualizada.")
                st.rerun()
        product_df = products_frame()
        st.write("Productos guardados")
        st.dataframe(product_df, width="stretch", hide_index=True)
        if not product_df.empty:
            selected_slug = st.selectbox("Producto", product_df["slug"].tolist())
            selected_product = saved_product(selected_slug)
            if selected_product:
                new_price = st.number_input(
                    "Precio USD",
                    min_value=1.0,
                    value=float(selected_product["price_usd"]),
                    step=1.0,
                )
                selected_product["price_usd"] = new_price
                col_update, col_delete = st.columns(2)
                if col_update.button("Actualizar precio", width="stretch"):
                    save_product(selected_product, "published")
                    st.success("Precio actualizado.")
                if col_delete.button("Eliminar producto", width="stretch"):
                    delete_product(selected_slug)
                    st.warning("Producto eliminado.")
                with st.expander("Versiones editables"):
                    version_df = product_versions_frame(selected_slug)
                    st.dataframe(version_df, width="stretch", hide_index=True)
                    if not version_df.empty:
                        version_options = {
                            f"v{int(row['version_number'])} - {row['status']} - {row['created_at']}": int(row["id"])
                            for _, row in version_df.iterrows()
                        }
                        selected_version_label = st.selectbox(
                            "Version",
                            list(version_options.keys()),
                            key="admin_product_version",
                        )
                        selected_version = saved_product_version(version_options[selected_version_label])
                        if selected_version:
                            st.download_button(
                                "Descargar version editable JSON",
                                data=json.dumps(selected_version, indent=2, ensure_ascii=False),
                                file_name=f"{selected_version['slug']}-version.json",
                                mime="application/json",
                                width="stretch",
                            )
                            col_restore, col_publish_version = st.columns(2)
                            if col_restore.button("Restaurar como borrador", width="stretch"):
                                save_product(selected_version, "draft")
                                st.success("Version restaurada como borrador.")
                                st.rerun()
                            if col_publish_version.button("Publicar esta version", width="stretch"):
                                save_product(selected_version, "published")
                                st.success("Version publicada.")
                                st.rerun()
                with st.expander("Registrar pago manual verificado"):
                    manual_provider = st.selectbox(
                        "Metodo verificado",
                        ["PayPal manual", "Bitcoin manual"],
                        key="manual_payment_provider",
                    )
                    manual_email = st.text_input("Email del comprador", key="manual_payment_email")
                    manual_order_id = st.text_input(
                        "ID de transaccion verificada",
                        key="manual_payment_order_id",
                        placeholder="PAYPAL-TXN-... o BTC-TXID-...",
                    )
                    st.caption(
                        "Usa esto solo despues de confirmar el pago en PayPal o en la red Bitcoin. "
                        "Genera link unico, recibo y email opcional."
                    )
                    if st.button("Confirmar pago manual y generar entrega", type="primary", width="stretch"):
                        if not manual_email or not manual_order_id:
                            st.error("Ingresa email del comprador e ID de transaccion verificada.")
                        else:
                            try:
                                download_url, expires_at, email_sent = confirm_manual_payment(
                                    manual_order_id,
                                    selected_product,
                                    manual_email,
                                    paypal,
                                    manual_provider.lower().replace(" ", "_"),
                                )
                                st.success("Pago manual registrado y entrega generada.")
                                st.code(download_url, language="text")
                                st.caption(f"Link valido hasta {expires_at} UTC o 3 descargas.")
                                if email_sent:
                                    st.info("Correo enviado al comprador.")
                                else:
                                    st.info("Correo no enviado: comparte el link manualmente o configura Resend.")
                            except Exception as exc:
                                st.error(f"No se pudo registrar el pago manual: {exc}")
        st.write("Pagos pendientes")
        st.dataframe(pending_payments_frame(), width="stretch", hide_index=True)
        st.write("Logs de auditoria")
        st.dataframe(audit_frame(), width="stretch", hide_index=True)


if __name__ == "__main__":
    main()
