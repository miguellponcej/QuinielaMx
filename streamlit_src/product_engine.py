from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any


BANNED_CLAIMS = (
    "garantizado",
    "dinero seguro",
    "hazte rico",
    "sin esfuerzo",
    "minar bitcoin",
    "seed phrase",
    "private key",
    "phishing",
    "hack",
)


@dataclass
class ProductDraft:
    niche: str
    product_type: str
    title: str
    subtitle: str
    description: str
    price_usd: float
    sales_bullets: list[str]
    table_of_contents: list[str]
    sections: list[dict[str, Any]]

    @property
    def slug(self) -> str:
        return slugify(self.title)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def product_from_dict(value: dict[str, Any]) -> ProductDraft:
    return ProductDraft(
        niche=str(value["niche"]),
        product_type=str(value["product_type"]),
        title=str(value["title"]),
        subtitle=str(value["subtitle"]),
        description=str(value["description"]),
        price_usd=float(value["price_usd"]),
        sales_bullets=list(value["sales_bullets"]),
        table_of_contents=list(value["table_of_contents"]),
        sections=list(value["sections"]),
    )


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")[:72] or "producto-digital"


def sanitize_copy(copy: str) -> str:
    safe = copy
    for claim in BANNED_CLAIMS:
        safe = re.sub(claim, "resultado potencial", safe, flags=re.IGNORECASE)
    return safe


def analyze_niche(market: str) -> dict[str, Any]:
    clean_market = sanitize_copy((market or "profesionales independientes").strip())
    problems = [
        f"No tienen un sistema claro para transformar conocimiento de {clean_market} en un producto descargable.",
        "Pierden tiempo respondiendo las mismas dudas de clientes uno por uno.",
        "Necesitan una oferta de bajo costo para validar demanda antes de crear algo mas grande.",
        "Tienen contenido disperso, pero no una pieza concreta que el comprador pueda usar hoy.",
        "Les cuesta explicar beneficios sin sonar exagerados o poco creibles.",
    ]
    ideas = [
        {
            "title": f"Checklist de accion rapida para {clean_market}",
            "type": "checklist",
            "price_usd": 9.0,
            "promise": "Diagnosticar la situacion y elegir el siguiente paso con claridad.",
        },
        {
            "title": f"Guia practica de 7 dias para {clean_market}",
            "type": "guia",
            "price_usd": 19.0,
            "promise": "Organizar una semana de ejecucion con tareas breves y medibles.",
        },
        {
            "title": f"Plantilla editable para {clean_market}",
            "type": "plantilla",
            "price_usd": 15.0,
            "promise": "Ahorrar tiempo con un documento listo para adaptar y usar.",
        },
        {
            "title": f"Reporte de oportunidades para {clean_market}",
            "type": "reporte",
            "price_usd": 29.0,
            "promise": "Entender errores frecuentes, patrones y oportunidades de mejora.",
        },
    ]
    return {
        "market": clean_market,
        "problems": problems,
        "customer_profile": (
            f"Persona con interes activo en {clean_market}, presupuesto limitado, urgencia por resolver "
            "un problema especifico y preferencia por herramientas practicas antes que teoria extensa."
        ),
        "value_props": [
            f"Convierte experiencia de {clean_market} en una herramienta concreta aplicable hoy.",
            "Reduce friccion con compra simple, descarga inmediata y pasos accionables.",
            "Permite validar demanda real antes de invertir semanas en un curso grande.",
        ],
        "ideas": ideas,
    }


def generate_product(market: str, idea: dict[str, Any] | None = None) -> ProductDraft:
    analysis = analyze_niche(market)
    selected = idea or analysis["ideas"][0]
    product_type = selected["type"]
    title = sanitize_copy(selected["title"])
    subtitle = f"Sistema practico para pasar de confusion a una accion concreta en {analysis['market']}."
    toc = [
        "Diagnostico del problema",
        "Mapa del cliente ideal",
        "Oferta digital simple",
        "Plan de entrega",
        "Checklist de publicacion",
        "Medicion y mejora",
    ]
    sections = [
        {
            "heading": "Diagnostico del problema",
            "body": [
                f"El comprador necesita entender que esta bloqueando su avance en {analysis['market']}.",
                "Lista sintomas, costo de no actuar y criterios para priorizar el primer cambio.",
                "La meta es entregar una herramienta practica, no prometer resultados fijos.",
            ],
        },
        {
            "heading": "Mapa del cliente ideal",
            "body": [
                analysis["customer_profile"],
                "Define una situacion concreta, una objecion frecuente y un resultado realista.",
            ],
        },
        {
            "heading": "Oferta digital simple",
            "body": [
                f"Producto recomendado: {product_type}. Precio inicial sugerido: ${selected['price_usd']:.2f} USD.",
                "Incluye una promesa acotada, entregables claros y una accion medible al final.",
            ],
        },
        {
            "heading": "Plan de entrega",
            "body": [
                "Prepara un PDF final y una version editable.",
                "Despues del pago, entrega el archivo solo al comprador confirmado.",
            ],
        },
        {
            "heading": "Checklist de publicacion",
            "body": [
                "Titulo claro, precio visible, beneficios especificos y boton de compra Stripe con PayPal como respaldo.",
                "Agrega FAQ, politica comercial y una descripcion honesta del producto.",
            ],
        },
        {
            "heading": "Medicion y mejora",
            "body": [
                "Registra ventas, ingresos, estado de pago y preguntas de clientes.",
                "Mejora la oferta con datos reales, no con promesas exageradas.",
            ],
        },
    ]
    return ProductDraft(
        niche=analysis["market"],
        product_type=product_type,
        title=title,
        subtitle=subtitle,
        description=f"{title} ayuda a compradores de {analysis['market']} a resolver un problema puntual con pasos claros.",
        price_usd=float(selected["price_usd"]),
        sales_bullets=[
            "Producto digital listo para descargar en PDF.",
            "Pagina de venta con beneficios, FAQ, garantia y precio.",
            "Copy de marketing para anuncios, redes, email y WhatsApp.",
            "Flujo Stripe preparado para ventas reales, con PayPal como respaldo.",
            "Contenido orientado a utilidad real, sin promesas de rentabilidad fija.",
        ],
        table_of_contents=toc,
        sections=sections,
    )


def marketing_assets(product: ProductDraft) -> list[dict[str, str]]:
    return [
        {
            "channel": "Facebook",
            "kind": "Ad",
            "copy": f"{product.title}: una herramienta descargable para organizar el siguiente paso en {product.niche}.",
        },
        {
            "channel": "Instagram",
            "kind": "Post",
            "copy": f"Menos teoria, mas accion. Convierte un problema puntual de {product.niche} en una checklist clara.",
        },
        {
            "channel": "TikTok",
            "kind": "Hook",
            "copy": f"Si estas atrapado en {product.niche}, aqui tienes una forma simple de decidir tu proximo paso.",
        },
        {
            "channel": "Google",
            "kind": "Search ad",
            "copy": f"{product.product_type} descargable para {product.niche}. Incluye pasos, checklist y PDF listo para usar.",
        },
        {
            "channel": "Email",
            "kind": "Follow-up",
            "copy": f"Gracias por tu interes en {product.title}. Esta pensado para resolver una situacion concreta.",
        },
        {
            "channel": "WhatsApp",
            "kind": "Mensaje",
            "copy": f"Te comparto {product.title}. Es un {product.product_type} practico con descarga inmediata.",
        },
    ]
