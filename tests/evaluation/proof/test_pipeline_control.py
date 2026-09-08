"""Provided-archive pipeline-control proof on a disposable copy."""

from pathlib import Path

import pytest

from arxiv_int.cli import main
from arxiv_int.evaluation.proof.control_copy import snapshot_sources
from arxiv_int.evaluation.proof.control_gates import GATE_NAMES, all_gates_passed
from arxiv_int.evaluation.proof.control_publish import publish_pipeline_control_proof
from arxiv_int.evaluation.proof.ops import check_capability_proof, publish_capability_proof
from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.quality.project_root import discover_project_root


def _seed_archive(root: Path) -> Path:
    archive = root / "archive"
    archive.mkdir()
    (archive / "keep.txt").write_text("keep\n", encoding="ascii")
    (archive / "change.txt").write_text("change\n", encoding="ascii")
    return archive


def test_pipeline_control_proof_passes_required_gates(tmp_path: Path) -> None:
    real_root = discover_project_root(Path(__file__))
    archive = _seed_archive(tmp_path)
    before = snapshot_sources((SiloRoot("default", archive),))
    published = publish_pipeline_control_proof(
        project_root=real_root,
        proof_id="pc-proof-1",
        results_dir=tmp_path / "results",
        archive_dir=archive,
    )
    after = snapshot_sources((SiloRoot("default", archive),))
    assert before.fingerprint == after.fingerprint
    assert (archive / "keep.txt").read_text(encoding="ascii") == "keep\n"
    assert published.directory.joinpath("export.json").is_file()
    export_text = published.directory.joinpath("export.json").read_text(encoding="utf-8")
    assert '"result": "no-export"' in export_text
    assert '"git_bound": []' in export_text
    gates_text = published.directory.joinpath("gates.json").read_text(encoding="utf-8")
    for name in GATE_NAMES:
        assert f'"{name}": "pass"' in gates_text
    check = check_capability_proof(published.directory, real_root, "unused")
    assert check == published.fingerprint
    summary = published.summary
    assert "pipeline-control" in summary
    assert "/home/" not in summary


def test_pipeline_control_dispatcher_and_cli(
    tmp_path: Path,
) -> None:
    real_root = discover_project_root(Path(__file__))
    archive = _seed_archive(tmp_path)
    published = publish_capability_proof(
        project_root=real_root,
        capability="pipeline-control",
        run_id="pc-cli-1",
        results_dir=tmp_path / "results-a",
        runs_dir=tmp_path / "runs-a",
        archive_dir=archive,
    )
    assert published.directory.joinpath("proof-manifest.json").is_file()
    code = main(
        [
            "evaluation",
            "proof",
            "publish",
            "--capability",
            "pipeline-control",
            "--run-id",
            "pc-cli-2",
            "--results-dir",
            str(tmp_path / "results-b"),
            "--runs-dir",
            str(tmp_path / "runs-b"),
            "--archive-dir",
            str(archive),
            "--project-root",
            str(real_root),
        ]
    )
    assert code == 0
    check_code = main(
        [
            "evaluation",
            "proof",
            "check",
            "--proof-dir",
            str(tmp_path / "results-b" / "proofs" / "pipeline-control" / "pc-cli-2"),
            "--project-root",
            str(real_root),
        ]
    )
    assert check_code == 0


def test_copy_bounded_skips_files_over_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from arxiv_int.evaluation.proof import control_copy

    monkeypatch.setattr(control_copy, "MAX_COPY_FILES", 2)
    monkeypatch.setattr(control_copy, "MAX_COPY_FILE_BYTES", 4)
    monkeypatch.setattr(control_copy, "MAX_COPY_TOTAL_BYTES", 8)
    archive = tmp_path / "src"
    archive.mkdir()
    (archive / "tiny.txt").write_bytes(b"ab")
    (archive / "huge.bin").write_bytes(b"x" * 32)
    dest = tmp_path / "dest"
    dest.mkdir()
    silos = control_copy.copy_bounded((SiloRoot("default", archive),), dest)
    names = {path.name for path in silos[0].root.rglob("*") if path.is_file()}
    assert "tiny.txt" in names
    assert "huge.bin" not in names
    assert (archive / "huge.bin").read_bytes() == b"x" * 32


def test_pipeline_control_refuses_an_unreadable_archive(tmp_path: Path) -> None:
    real_root = discover_project_root(Path(__file__))
    missing = tmp_path / "missing-archive"
    with pytest.raises(ValueError, match="no readable files"):
        publish_pipeline_control_proof(
            project_root=real_root,
            proof_id="pc-missing",
            results_dir=tmp_path / "results",
            archive_dir=missing,
        )


def test_gate_helper_requires_every_named_gate() -> None:
    assert "noop_zero_workers" in GATE_NAMES
    complete = {name: "pass" for name in GATE_NAMES}
    assert all_gates_passed(complete)
    incomplete = {name: "pass" for name in GATE_NAMES if name != "no_export"}
    assert not all_gates_passed(incomplete)
