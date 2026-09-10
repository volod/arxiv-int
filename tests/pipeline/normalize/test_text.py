from arxiv_int.pipeline.normalize.text import canonical_view, load_offset_map, search_view


def test_canonical_view_maps_every_offset_back_to_its_source() -> None:
    original = "A\r\nB\u0301\ufeff  C\x00\n"
    view = canonical_view(original)

    assert view.text == "A\nB\u0301  C\n"
    assert [original[run.source_start : run.source_end] for run in view.offsets.runs] == [
        "A",
        "\r\n",
        "B\u0301",
        "  C",
        "\n",
    ]
    sources = [view.offsets.to_source(index) for index in range(len(view.text))]
    assert sources == sorted(sources)
    assert sources[0] == 0
    assert sources[-1] < len(original)


def test_canonical_view_round_trips_a_composed_character() -> None:
    view = canonical_view("e\u0301tat")

    assert view.text == "\u00e9tat"
    assert view.offsets.to_source(1) == 2
    assert view.offsets.to_target(2) == 1


def test_search_view_collapses_whitespace_and_folds_case() -> None:
    canonical = "  \u0421\u0451\u0440\u044b\u0439   Kot\n\n"
    view = search_view(canonical)

    assert view.text == "\u0441\u0435\u0440\u044b\u0439 kot"
    assert view.offsets.to_source(0) == 2
    assert canonical[view.offsets.to_source(len(view.text) - 1)] == "t"


def test_offset_map_survives_serialization() -> None:
    view = canonical_view("A\r\nB")
    restored = load_offset_map(view.offsets.serialize())

    assert restored.serialize() == view.offsets.serialize()
    assert restored.to_source(2) == 3
