import sys
from pathlib import Path

import pytest

from arxiv_int.features import MissingFeatureError, feature_group
from arxiv_int.interfaces.pipeline import StageContext
from arxiv_int.transformations.invoke import dbt_cli_args, invoke_dbt
from arxiv_int.transformations.polars_prep import prepare_document_frame, run_polars_prepare


def test_dbt_cli_args_include_isolation_and_bounds(tmp_path: Path) -> None:
    args = dbt_cli_args(
        "build",
        project_dir=tmp_path / "project",
        profiles=tmp_path / "profiles",
        target_dir=tmp_path / "target",
        log_dir=tmp_path / "logs",
        select=("tag:fixture", "tag:quality"),
        vars_payload='{"generation_id": "r1"}',
        full_refresh=True,
        threads=2,
    )
    assert args[0] == "build"
    assert "--project-dir" in args
    assert "--full-refresh" in args
    assert args[args.index("--threads") + 1] == "2"
    parse_args = dbt_cli_args(
        "parse",
        project_dir=tmp_path / "project",
        profiles=tmp_path / "profiles",
        target_dir=tmp_path / "target",
        log_dir=tmp_path / "logs",
        select=("tag:fixture",),
        vars_payload="{}",
        full_refresh=False,
        threads=2,
    )
    assert "--select" not in parse_args


def test_invoke_dbt_reports_a_missing_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    from arxiv_int.transformations import invoke as invoke_mod

    def _missing(name: str) -> object:
        raise MissingFeatureError(feature_group("transform"), name)

    monkeypatch.setattr(invoke_mod, "require_module", _missing)
    outcome = invoke_dbt(["parse"], credentials=None)
    assert outcome.success is False
    assert "transform" in outcome.detail


def test_prepare_document_frame_strips_and_refuses_lazy_inputs() -> None:
    polars = pytest.importorskip("polars")
    frame = polars.DataFrame({"document_id": [" doc-1 "], "title": [" a "]})
    prepared = prepare_document_frame(frame)
    assert prepared.get_column("document_id").to_list() == ["doc-1"]
    assert prepared.get_column("title").to_list() == ["a"]
    with pytest.raises(TypeError, match="materialized"):
        prepare_document_frame([{"document_id": "x"}])


def test_polars_prepare_uses_the_stage_seam() -> None:
    polars = pytest.importorskip("polars")
    context = StageContext(
        stage="normalize",
        run_id="r1",
        archive_dir=Path("."),
        results_dir=Path("."),
        options={"contract_version": "1.0.0"},
    )
    prepared, result = run_polars_prepare(context, polars.DataFrame({"document_id": ["a"]}))
    assert result.outcome == "completed"
    assert result.outputs[0].dataset == "documents"
    assert prepared.height == 1


def test_base_import_does_not_load_dbt() -> None:
    sys.modules.pop("dbt", None)
    sys.modules.pop("dbt.cli.main", None)
    import arxiv_int.cli as cli_mod
    import arxiv_int.transformations as transform_mod

    assert (
        cli_mod.build_parser().parse_args(["transform", "parse", "--run-id", "r"]).transform_command
        == "parse"
    )
    assert "dbt.cli.main" not in sys.modules
    assert transform_mod.METHOD == "dbt"
