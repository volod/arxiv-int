"""Revision graph, checksum immutability, and contract-to-history drift checks."""

import json
from pathlib import Path

from arxiv_int.contracts.migrations.authoring import generate_revision, read_manifest
from arxiv_int.contracts.migrations.check import check_migrations
from arxiv_int.contracts.migrations.graph import (
    graph_findings,
    head_state_findings,
    manifest_findings,
)
from arxiv_int.contracts.migrations.paths import (
    head_state_path,
    revision_manifest_path,
    versions_dir,
)
from arxiv_int.resources.paths import contracts_root
from tests.contracts.migrations._project import disposable_project, product_root


def _prepared(tmp_path: Path) -> Path:
    root = disposable_project(tmp_path / "project")
    generate_revision(root, root / "contracts", message="baseline contract schema")
    return root


def test_product_tree_has_one_head_and_no_pending_revision() -> None:
    root = product_root()
    report = check_migrations(root, contracts_root())
    assert report.ok, report.findings
    assert report.pending_operations == ()
    assert report.head == "0001"
    assert report.live_evidence == "not-run"


def test_generated_revision_files_are_deterministic(tmp_path: Path) -> None:
    left = _prepared(tmp_path / "left")
    right = _prepared(tmp_path / "right")
    name = "0001_baseline_contract_schema.py"
    assert (versions_dir(left) / name).read_text(encoding="utf-8") == (
        versions_dir(right) / name
    ).read_text(encoding="utf-8")


def test_second_revision_only_covers_the_new_change(tmp_path: Path) -> None:
    root = _prepared(tmp_path)
    baseline = (versions_dir(root) / "0001_baseline_contract_schema.py").read_text(encoding="utf-8")
    contract = root / "contracts" / "datasets" / "documents.odcs.yaml"
    contract.write_text(
        contract.read_text(encoding="utf-8")
        + "      - name: page_count\n        logicalType: integer\n",
        encoding="utf-8",
    )
    candidate = generate_revision(root, root / "contracts", message="add page count")
    assert candidate.revision == "0002"
    assert [operation.kind for operation in candidate.operations] == ["add_column"]
    text = candidate.path.read_text(encoding="utf-8")
    assert 'op.add_column("documents", sa.Column("page_count"' in text
    # Old revisions never follow later contract edits.
    assert (versions_dir(root) / "0001_baseline_contract_schema.py").read_text(
        encoding="utf-8"
    ) == baseline
    assert check_migrations(root, root / "contracts").ok


def test_contract_change_without_a_revision_fails(tmp_path: Path) -> None:
    root = _prepared(tmp_path)
    contract = root / "contracts" / "datasets" / "documents.odcs.yaml"
    contract.write_text(
        contract.read_text(encoding="utf-8")
        + "      - name: page_count\n        logicalType: integer\n",
        encoding="utf-8",
    )
    report = check_migrations(root, root / "contracts")
    assert not report.ok
    assert report.pending_operations == ("add_column corpus.documents.page_count",)
    assert any("no matching revision" in item for item in report.findings)


def test_edited_revision_fails_the_checksum_gate(tmp_path: Path) -> None:
    root = _prepared(tmp_path)
    path = versions_dir(root) / "0001_baseline_contract_schema.py"
    path.write_text(
        path.read_text(encoding="utf-8") + "\n# edited after review\n", encoding="utf-8"
    )
    findings = manifest_findings(root)
    assert findings == [
        "revision 0001 was edited after review: 0001_baseline_contract_schema.py checksum changed"
    ]


def test_unlisted_and_missing_revision_files_fail(tmp_path: Path) -> None:
    root = _prepared(tmp_path)
    (versions_dir(root) / "0009_untracked.py").write_text("revision = '0009'\n", encoding="utf-8")
    assert any("not listed in the manifest" in item for item in manifest_findings(root))
    (versions_dir(root) / "0001_baseline_contract_schema.py").unlink()
    assert any("missing revision file" in item for item in manifest_findings(root))


def test_multiple_heads_fail(tmp_path: Path) -> None:
    root = _prepared(tmp_path)
    source = versions_dir(root) / "0001_baseline_contract_schema.py"
    fork = versions_dir(root) / "0002_fork.py"
    fork.write_text(
        source.read_text(encoding="utf-8").replace(
            'revision: str = "0001"', 'revision: str = "0002"'
        ),
        encoding="utf-8",
    )
    findings = graph_findings(root)
    assert any("multiple heads" in item for item in findings)


def test_missing_parent_revision_fails(tmp_path: Path) -> None:
    root = _prepared(tmp_path)
    path = versions_dir(root) / "0001_baseline_contract_schema.py"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "down_revision: str | None = None", 'down_revision: str | None = "0000"'
        ),
        encoding="utf-8",
    )
    assert any("revision graph is invalid" in item for item in graph_findings(root))


def test_cyclic_revision_graph_fails(tmp_path: Path) -> None:
    root = _prepared(tmp_path)
    path = versions_dir(root) / "0001_baseline_contract_schema.py"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "down_revision: str | None = None", 'down_revision: str | None = "0001"'
        ),
        encoding="utf-8",
    )
    assert any("revision graph is invalid" in item for item in graph_findings(root))


def test_missing_runner_is_reported(tmp_path: Path, monkeypatch) -> None:
    root = _prepared(tmp_path)
    monkeypatch.setattr("arxiv_int.contracts.migrations.graph.runner_available", lambda: False)
    assert graph_findings(root) == [
        "alembic is not installed; the revision graph could not be checked"
    ]


def test_head_state_must_name_the_manifest_head(tmp_path: Path) -> None:
    root = _prepared(tmp_path)
    path = head_state_path(root)
    state = json.loads(path.read_text(encoding="utf-8"))
    state["revision"] = "0009"
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    assert any("frozen head state names revision" in item for item in head_state_findings(root))
    path.unlink()
    assert any("frozen head state is missing" in item for item in head_state_findings(root))


def test_manifest_records_parents_and_checksums(tmp_path: Path) -> None:
    root = _prepared(tmp_path)
    manifest = read_manifest(root)
    assert manifest["revisions"]["0001"]["downRevision"] is None
    assert len(manifest["revisions"]["0001"]["sha256"]) == 64
    assert revision_manifest_path(root).is_file()


def test_no_revision_is_written_without_a_contract_change(tmp_path: Path) -> None:
    root = _prepared(tmp_path)
    candidate = generate_revision(root, root / "contracts", message="no change")
    assert not candidate.created
    assert candidate.revision == "0001"
    assert len(list(versions_dir(root).glob("0*.py"))) == 1
