from src.active_draws.progol_es_client import parse_progol_es_reference, secondary_url_for_game


def test_secondary_url_for_media_semana():
    assert "progol_media_semana" in secondary_url_for_game("progol_media_semana")


def test_parse_progol_es_reference_extracts_program_image():
    html = """
    <html><body>
      <h1>Programa y momios</h1>
      <img src="/images/resultados_media.jpg?id=797" />
      <a>Archivo:796</a>
      <a>Archivo:797</a>
    </body></html>
    """

    draw = parse_progol_es_reference(
        html,
        "progol_media_semana",
        "Progol Media Semana",
        "https://www.progol.es/progol_media_semana.html?id=progol_media_semana",
    )

    assert draw["draw_number"] == "797"
    assert draw["source_artifacts"][0]["type"] == "image"
    assert "resultados_media.jpg" in draw["source_artifacts"][0]["url"]
