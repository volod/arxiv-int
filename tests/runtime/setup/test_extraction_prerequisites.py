from pathlib import Path

from arxiv_int.runtime import load_runtime_config
from arxiv_int.runtime.setup.models import run_models_phase
from tests.runtime.setup.conftest import checkout, completed, operator_env


def test_models_phase_prefetches_docling_into_configured_cache(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    environment = operator_env(tmp_path, root)
    config = load_runtime_config(project_root=root, environment=environment)
    commands: list[tuple[str, ...]] = []

    def runner(command: tuple[str, ...], **kwargs: object):
        commands.append(command)
        return completed()

    result = run_models_phase(
        config,
        downloads=True,
        runner=runner,
        listed={"fixture-model"},
        extraction_required=True,
    )

    assert result.status == "ready"
    assert commands[0] == (
        str(root / ".venv/bin/docling-tools"),
        "models",
        "download",
        "layout",
        "tableformer",
        "--output-dir",
        str(config.model_cache_dir / "docling"),
    )


def test_offline_setup_refuses_missing_docling_models(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    environment = operator_env(tmp_path, root)
    config = load_runtime_config(project_root=root, environment=environment)

    result = run_models_phase(
        config,
        downloads=False,
        runner=lambda *args, **kwargs: completed(),
        listed={"fixture-model"},
        extraction_required=True,
    )

    assert result.status == "blocked"
    assert result.action == "set SETUP_DOWNLOADS=1, then make setup"
