from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st

from streamlit_src.paypal import PayPalConfig, capture_order, create_order
from streamlit_src.pdf_delivery import product_pdf_bytes
from streamlit_src.product_engine import analyze_niche, generate_product, marketing_assets


APP_NAME = "AI Digital Product Money Machine"
DB_PATH = Path("data/streamlit_sales.db")


st.set_page_config(page_title=APP_NAME, page_icon="💼", layout="wide")


def secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default))
    except Exception:
        return default


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
        app_base_url=secret("APP_BASE_URL", "http://localhost:8501").rstrip("/"),
    )


def render_security_notice() -> None:
    st.info(
        "Venta legitima: PayPal procesa el pago. Esta app no guarda tarjetas, cuentas bancarias, "
        "seed phrases, private keys ni contrasenas de wallet."
    )


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
            payload = capture_order(config, str(token))
            record_sale(str(token), product, payload)
            st.success("Pago confirmado. Tu descarga esta lista.")
            st.download_button(
                "Descargar PDF comprado",
                data=product_pdf_bytes(generate_product(product["niche"])),
                file_name=f"{product['slug']}.pdf",
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
        btc_address = secret("OWNER_BTC_PUBLIC_ADDRESS", "")
        st.text_input("Wallet BTC publica", value=btc_address, disabled=True)
        st.caption("Solo referencia publica. No se solicitan ni guardan llaves privadas.")

    tab_build, tab_landing, tab_sales, tab_marketing = st.tabs(
        ["Producto", "Landing y checkout", "Ventas", "Marketing"]
    )

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
                        st.session_state["last_paypal_order"] = order
                        st.success("Orden creada. Abre PayPal para completar el pago.")
                    except Exception as exc:
                        st.error(f"No se pudo crear la orden PayPal: {exc}")
            order = st.session_state.get("last_paypal_order")
            if order:
                st.link_button("Pagar con PayPal", order["approval_url"], width="stretch")
        else:
            st.warning(
                "Configura PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_MODE y APP_BASE_URL "
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
