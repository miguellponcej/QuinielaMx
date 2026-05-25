from src.active_draws.local_ocr_extractor import parse_ocr_text_to_draw


def test_parse_ocr_text_to_draw_accepts_complete_numbered_vs_rows():
    text = """
    CONCURSO 797
    Juegos del martes 26 al jueves 28 de mayo
    1 EQUIPO A VS EQUIPO B
    2 EQUIPO C VS EQUIPO D
    3 EQUIPO E VS EQUIPO F
    4 EQUIPO G VS EQUIPO H
    5 EQUIPO I VS EQUIPO J
    6 EQUIPO K VS EQUIPO L
    7 EQUIPO M VS EQUIPO N
    8 EQUIPO O VS EQUIPO P
    9 EQUIPO Q VS EQUIPO R
    """

    draw = parse_ocr_text_to_draw(
        text,
        "progol_media_semana",
        "Progol Media Semana",
        "https://pronosticos.gob.mx/ProgolMediaSemana/Quiniela",
    )

    assert draw is not None
    assert draw["draw_number"] == "797"
    assert len(draw["matches"]) == 9
    assert draw["matches"][0]["local"] == "EQUIPO A"
    assert draw["matches"][0]["visitante"] == "EQUIPO B"


def test_parse_ocr_text_to_draw_rejects_incomplete_program():
    text = "CONCURSO 797\n1 EQUIPO A VS EQUIPO B\n2 EQUIPO C VS EQUIPO D"

    draw = parse_ocr_text_to_draw(
        text,
        "progol_media_semana",
        "Progol Media Semana",
        "https://pronosticos.gob.mx/ProgolMediaSemana/Quiniela",
    )

    assert draw is None
