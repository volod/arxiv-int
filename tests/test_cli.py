import logging

from arxiv_int.cli import build_parser, main


def test_parser_selects_the_info_command() -> None:
    assert build_parser().parse_args(["info"]).command == "info"


def test_info_command_logs_the_project_identity(caplog) -> None:  # type: ignore[no-untyped-def]
    caplog.set_level(logging.INFO)

    assert main(["info"]) == 0
    assert "arxiv-int" in caplog.text
    assert "arxiv_int" in caplog.text


def test_parser_accepts_a_stage_filter_for_features() -> None:
    arguments = build_parser().parse_args(["features", "--stage", "embed"])

    assert arguments.command == "features"
    assert arguments.stage == "embed"


def test_features_command_logs_groups_with_install_commands(caplog) -> None:  # type: ignore[no-untyped-def]
    caplog.set_level(logging.INFO)

    assert main(["features"]) == 0
    assert "feature groups" in caplog.text
    assert "uv pip install 'arxiv-int[lake]'" in caplog.text
    assert "reserved for capability: russian-nlp" in caplog.text


def test_features_command_reports_an_unknown_stage(caplog) -> None:  # type: ignore[no-untyped-def]
    caplog.set_level(logging.INFO)

    assert main(["features", "--stage", "no-such-stage"]) == 1
    assert "unknown stage" in caplog.text
