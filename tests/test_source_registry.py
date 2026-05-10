from src.data_sources.source_registry import source_registry_as_dicts, sources_for_game


def test_registry_includes_requested_web_sources():
    sources = source_registry_as_dicts()
    ids = {source["source_id"] for source in sources}

    assert "tulotero_mx" in ids
    assert "caliente_liga_mx" in ids
    assert "bet365_football" in ids
    assert "the_odds_api" in ids


def test_sports_sources_are_ordered_by_priority():
    sources = sources_for_game("progol")
    priorities = [source.priority for source in sources]

    assert priorities == sorted(priorities, reverse=True)
    assert sources[0].category == "official"
