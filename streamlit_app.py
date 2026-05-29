from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import pandas as pd
import requests
import streamlit as st

from streamlit_src.paypal import PayPalConfig, capture_order, create_order, paypal_access_token
from streamlit_src.pdf_delivery import product_pdf_bytes
from streamlit_src.product_engine import analyze_niche, generate_product, marketing_assets, product_from_dict


APP_NAME = "AI Digital Product Money Machine"
DB_PATH = Path("data/streamlit_sales.db")
DEPLOY_FILE_URL = (
    "https://github.com/miguellponcej/QuinielaMx/blob/"
    "ai-money-machine-streamlit/streamlit_app.py"
)
GITHUB_BRANCH_URL = "https://github.com/miguellponcej/QuinielaMx/tree/ai-money-machine-streamlit"
SECRETS_TEMPLATE = """APP_BASE_URL = ""
PAYPAL_MODE = "sandbox"
PAYPAL_CLIENT_ID = "your-paypal-client-id"
PAYPAL_CLIENT_SECRET = "your-paypal-client-secret"
OWNER_BTC_PUBLIC_ADDRESS = "your-public-btc-address"
"""


st.set_page_config(page_title=APP_NAME, page_icon="💼", layout="wide")


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


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
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
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def pending_product_for_order(order_id: str) -> dict[str, Any] | None:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "select product_json from pending_orders where paypal_order_id = ?",
            (order_id,),
        ).fetchone()
    if not row:
        return None
    return json.loads(row[0])


def record_sale(order_id: str, product: dict[str, Any], capture_payload: dict[str, Any]) -> None:
    payer = capture_payload.get("payer", {})
    email = payer.get("email_address", "")
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
                capture_payload.get("status", "CAPTURED"),
                datetime.now(timezone.utc).isoformat(),
                json.dumps(capture_payload),
            ),
        )


def sales_frame() -> pd.DataFrame:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query("select * from sales order by captured_at desc", conn)


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


def render_security_notice() -> None:
    st.info(
        "Venta legitima: PayPal procesa el pago. Esta app no guarda tarjetas, cuentas bancarias, "
        "seed phrases, private keys ni contrasenas de wallet."
    )


def missing_setup_items(config: PayPalConfig, btc_address: str) -> list[str]:
    missing = []
    if not config.client_id.strip() or config.client_id.startswith(("replace", "your-")):
        missing.append("PAYPAL_CLIENT_ID")
    if not config.client_secret.strip() or config.client_secret.startswith(("replace", "your-")):
        missing.append("PAYPAL_CLIENT_SECRET")
    if config.mode not in {"sandbox", "live"}:
        missing.append("PAYPAL_MODE debe ser sandbox o live")
    if not btc_address.strip() or btc_address.startswith(("replace", "your-")):
        missing.append("OWNER_BTC_PUBLIC_ADDRESS")
    return missing


def render_setup_tab(config: PayPalConfig, btc_address: str) -> None:
    st.subheader("Setup de Streamlit, GitHub y PayPal")
    st.write("Usa estos datos para levantar la app en Streamlit Cloud desde tu GitHub.")
    col_a, col_b = st.columns(2)
    col_a.link_button("Abrir archivo para Streamlit", DEPLOY_FILE_URL, width="stretch")
    col_b.link_button("Abrir rama en GitHub", GITHUB_BRANCH_URL, width="stretch")
    st.code(DEPLOY_FILE_URL, language="text")

    st.write("Pega esta plantilla en Streamlit Cloud > App > Settings > Secrets.")
    st.code(SECRETS_TEMPLATE, language="toml")
    st.caption("APP_BASE_URL puede quedar vacio; la app detecta su URL publica para el retorno de PayPal.")

    missing = missing_setup_items(config, btc_address)
    if missing:
        st.warning("Configuracion pendiente: " + ", ".join(missing))
    else:
        st.success("Los secretos basicos estan presentes.")

    st.write("Estado detectado")
    status_col_1, status_col_2, status_col_3 = st.columns(3)
    status_col_1.metric("PayPal", "listo" if config.is_configured else "pendiente")
    status_col_2.metric("Modo", config.mode)
    status_col_3.metric("Wallet BTC", "lista" if btc_address.strip() else "pendiente")
    st.caption(f"URL de retorno PayPal detectada: {config.app_base_url}")

    if st.button("Probar conexion PayPal", width="stretch"):
        if not config.is_configured:
            st.error("Agrega PAYPAL_CLIENT_ID y PAYPAL_CLIENT_SECRET en Streamlit Secrets antes de probar.")
        else:
            with st.spinner("Probando credenciales con PayPal..."):
                try:
                    paypal_access_token(config)
                    st.success("PayPal respondio correctamente. El checkout puede crear ordenes.")
                except Exception as exc:
                    st.error(f"PayPal no respondio con esas credenciales: {exc}")


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
            st.success("Pago confirmado. Tu descarga esta lista.")
            st.download_button(
                "Descargar PDF comprado",
                data=product_pdf_bytes(product_from_dict(purchased_product)),
                file_name=f"{purchased_product['slug']}.pdf",
                mime="application/pdf",
                width="stretch",
            )
            return True
        except Exception as exc:
            st.error(f"No se pudo capturar el pago de PayPal: {exc}")
            return False


def main() -> None:
    init_db()
    config = paypal_config()

    st.title(APP_NAME)
    st.caption("Crea, publica, cobra con PayPal y entrega productos digitales reales.")
    render_security_notice()

    with st.sidebar:
        st.header("Configuracion")
        st.write("PayPal:", "configurado" if config.is_configured else "pendiente")
        st.write("Modo:", config.mode)
        st.caption(f"Retorno PayPal: {config.app_base_url}")
        btc_address = secret("OWNER_BTC_PUBLIC_ADDRESS", "")
        st.text_input("Wallet BTC publica", value=btc_address, disabled=True)
        st.caption("Solo referencia publica. No se solicitan ni guardan llaves privadas.")

    tab_setup, tab_build, tab_landing, tab_sales, tab_marketing = st.tabs(
        ["Setup", "Producto", "Landing y checkout", "Ventas", "Marketing"]
    )

    with tab_setup:
        render_setup_tab(config, btc_address)

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
        product_dict = product.to_dict()
        product_dict["slug"] = product.slug

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

    with tab_landing:
        capture_return_if_needed(product_dict, config)
        st.subheader(product.title)
        st.write(product.subtitle)
        for bullet in product.sales_bullets:
            st.write(f"- {bullet}")
        st.divider()
        st.metric("Precio", f"${product.price_usd:.2f} USD")

        if config.is_configured:
            if st.button("Crear checkout PayPal", type="primary", width="stretch"):
                with st.spinner("Creando orden PayPal..."):
                    try:
                        order = create_order(config, product_dict)
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

        st.info("Despues del retorno de PayPal, la app captura la orden y habilita la descarga del PDF.")

    with tab_sales:
        df = sales_frame()
        gross = float(df["amount_usd"].sum()) if not df.empty else 0.0
        rate = btc_rate_usd()
        col1, col2, col3 = st.columns(3)
        col1.metric("Ventas registradas", str(len(df)))
        col2.metric("Ingresos brutos", f"${gross:.2f} USD")
        col3.metric("Equivalente BTC", f"{(gross / rate if rate else 0):.8f}")
        st.dataframe(df, width="stretch", hide_index=True)
        st.download_button(
            "Exportar ventas CSV",
            data=df.to_csv(index=False),
            file_name="sales-report.csv",
            mime="text/csv",
            width="stretch",
        )

    with tab_marketing:
        st.subheader("Copies generados")
        for asset in marketing_assets(product):
            with st.expander(f"{asset['channel']} - {asset['kind']}"):
                st.write(asset["copy"])


if __name__ == "__main__":
    main()
