"""New inventory run snapshots preserve links and never read source contents."""

from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.pipeline.commands import create_run_context
from arxiv_int.pipeline.inventory.snapshot import INVENTORY_METADATA_POLICY, inventory_snapshot


def test_link_change_changes_metadata_identity(tmp_path: Path) -> None:
    link = tmp_path / "link"
    link.symlink_to(tmp_path / "missing-one")
    silos = (SiloRoot("one", tmp_path),)
    first = inventory_snapshot(silos)
    assert inventory_snapshot(silos) == first
    link.unlink()
    link.symlink_to(tmp_path / "missing-two")
    assert inventory_snapshot(silos) != first


def test_snapshot_is_order_independent_and_preserves_silo_identity(tmp_path: Path) -> None:
    from arxiv_int.pipeline.inventory import snapshot
    from arxiv_int.pipeline.inventory.walk import Entry

    entries = [Entry("a", "file", (1,)), Entry("b", "link", (2,))]
    silos = (SiloRoot("one", tmp_path),)
    with patch.object(snapshot, "walk", return_value=iter(entries)):
        first = inventory_snapshot(silos)
    with patch.object(snapshot, "walk", return_value=iter(reversed(entries))):
        assert inventory_snapshot(silos) == first
    with patch.object(snapshot, "walk", return_value=iter(entries)):
        assert inventory_snapshot((replace(silos[0], silo_id="two"),)) != first


def test_run_creation_does_not_open_source_files(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "unreadable").write_bytes(b"source content")
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text("[project]\nname='fixture'\n")
    original = Path.open

    def guarded(path: Path, *args: object, **kwargs: object):
        if path.is_relative_to(source):
            raise AssertionError("source content read before inventory")
        return original(path, *args, **kwargs)

    with patch.object(Path, "open", guarded):
        context = create_run_context(
            project_root=project,
            environment={
                "ARCHIVE_DIR": str(source),
                "RESULTS_DIR": str(tmp_path / "results"),
                "PGDATA_DIR": str(tmp_path / "pgdata"),
            },
        )
    assert context.source_drift_policy == INVENTORY_METADATA_POLICY


def test_source_change_before_worker_cannot_use_frozen_identity(tmp_path: Path) -> None:
    import pytest

    from arxiv_int.pipeline.dag.execute import stage_context
    from arxiv_int.pipeline.inventory.stage import InventoryStage
    from tests.pipeline.conftest import make_context

    run = make_context(tmp_path, profile="investigation")
    frozen = inventory_snapshot(run.silos)
    run = replace(
        run,
        project_root=Path.cwd(),
        source_snapshot=frozen,
        source_metadata_snapshot=frozen,
        source_drift_policy=INVENTORY_METADATA_POLICY,
    )
    (run.silos[0].root / "doc.txt").write_text("changed after the command loaded its run")
    with pytest.raises(ValueError, match="frozen source set"):
        InventoryStage().run(stage_context(run, "inventory"))
    assert not list(run.results_dir.rglob("inventory.json"))
