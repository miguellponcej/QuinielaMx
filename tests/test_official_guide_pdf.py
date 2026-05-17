"""Tests for official guide PDF parser."""

from src.active_draws.official_guide_pdf import extract_guide_pdf_urls, parse_guide_text


def test_extract_media_semana_guide_pdf_url() -> None:
    html = '<a href="../../Documentos/juegos/Concursosysorteos/progol_media_guia_quiniela/guiamedia.pdf?v=15052026181109">Guia</a>'

    urls = extract_guide_pdf_urls(html, "https://pronosticos.gob.mx/ProgolMediaSemana/Quiniela", "progol_media_semana")

    assert urls == [
        "https://pronosticos.gob.mx/Documentos/juegos/Concursosysorteos/progol_media_guia_quiniela/guiamedia.pdf?v=15052026181109"
    ]


def test_parse_media_semana_guide_text_into_nine_matches() -> None:
    text = """
    GUIA DE LA QUINIELA CONCURSO 873
    Juegos del miercoles 20 al jueves 21 de mayo 2026
    CASILLERO 1
    LOCAL VISITANTE
    PACHUCA VS TOLUCA
    CASILLERO 2
    CRUZ AZUL
    VS
    AMERICA
    CASILLERO 3
    TIGRES VS MONTERREY
    CASILLERO 4
    PUMAS VS LEON
    CASILLERO 5
    SANTOS VS ATLAS
    CASILLERO 6
    NECAXA VS JUAREZ
    CASILLERO 7
    CHIVAS VS MAZATLAN
    CASILLERO 8
    TIJUANA VS QUERETARO
    CASILLERO 9
    PUEBLA VS SAN LUIS
    """

    draw = parse_guide_text(
        text,
        "progol_media_semana",
        "Progol Media Semana",
        "https://pronosticos.gob.mx/guia.pdf",
    )

    assert draw["draw_number"] == "873"
    assert draw["draw_date"] == "miercoles 20 al jueves 21 de mayo 2026"
    assert len(draw["matches"]) == 9
    assert draw["matches"][0]["local"] == "PACHUCA"
    assert draw["matches"][0]["visitante"] == "TOLUCA"
    assert draw["matches"][1]["local"] == "CRUZ AZUL"
    assert draw["matches"][1]["visitante"] == "AMERICA"
