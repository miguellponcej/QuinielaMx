from __future__ import annotations

from io import BytesIO
from textwrap import wrap

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from streamlit_src.product_engine import ProductDraft


def _draw_wrapped(pdf: canvas.Canvas, text: str, x: int, y: int, width_chars: int = 92, line_height: int = 14) -> int:
    for line in wrap(text, width_chars):
        pdf.drawString(x, y, line)
        y -= line_height
    return y


def product_pdf_bytes(product: ProductDraft) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    x = 54
    y = int(height - 54)

    def ensure_space(min_y: int = 72) -> None:
        nonlocal y
        if y < min_y:
            pdf.showPage()
            y = int(height - 54)

    pdf.setTitle(product.title)
    pdf.setFont("Helvetica-Bold", 18)
    y = _draw_wrapped(pdf, product.title, x, y, 62, 22)
    pdf.setFont("Helvetica", 11)
    y = _draw_wrapped(pdf, product.subtitle, x, y - 8, 88, 16)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(x, y - 8, f"Precio sugerido: ${product.price_usd:.2f} USD")
    y -= 36

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(x, y, "Indice")
    y -= 20
    pdf.setFont("Helvetica", 11)
    for index, item in enumerate(product.table_of_contents, start=1):
        ensure_space()
        pdf.drawString(x, y, f"{index}. {item}")
        y -= 16

    y -= 12
    for section in product.sections:
        ensure_space(110)
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(x, y, section["heading"])
        y -= 20
        pdf.setFont("Helvetica", 10)
        for paragraph in section["body"]:
            ensure_space()
            y = _draw_wrapped(pdf, paragraph, x, y, 96, 14)
            y -= 6
        y -= 8

    ensure_space(110)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(x, y, "Nota de uso responsable")
    y -= 18
    pdf.setFont("Helvetica", 10)
    _draw_wrapped(
        pdf,
        "Este producto entrega informacion y herramientas practicas. No promete ingresos garantizados, "
        "no solicita datos sensibles de pago y no contiene instrucciones para manipular sistemas o fondos.",
        x,
        y,
        96,
        14,
    )

    pdf.save()
    return buffer.getvalue()
