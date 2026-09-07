from pathlib import Path

import pytest

from arxiv_int.runtime import (
    FilesystemEvidence,
    RuntimeConfig,
    create_results_layout,
    load_runtime_config,
    resolve_allowed_path,
    validate_runtime_paths,
)


def test_path_resolution_is_symlink_safe_and_fail_closed(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    document = outside / "proof.txt"
    document.write_text("proof", encoding="utf-8")
    (allowed / "escape").symlink_to(outside, target_is_directory=True)

    assert resolve_allowed_path(document, ()) is None
    assert resolve_allowed_path(allowed / "escape" / document.name, (allowed,), kind="file") is None
    assert resolve_allowed_path(allowed, (allowed,), kind="directory") == allowed.resolve()


def _runtime_config(tmp_path: Path, **overrides: str) -> RuntimeConfig:
    checkout = tmp_path / "checkout"
    checkout.mkdir(parents=True)
    (checkout / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    archive = tmp_path / "archive"
    archive.mkdir()
    values = {
        "ARCHIVE_DIR": str(archive),
        "RESULTS_DIR": str(tmp_path / "results"),
        "PGDATA_DIR": str(tmp_path / "pgdata"),
        **overrides,
    }
    return load_runtime_config(project_root=checkout, environment=values)


def _evidence(
    path: Path,
    *,
    filesystem: str = "ext4",
    device: str = "8:1",
    rotational: bool | None = False,
    ownership: bool = True,
    read_only: bool = False,
    free_bytes: int = 1_000_000,
) -> FilesystemEvidence:
    return FilesystemEvidence(
        path=path,
        filesystem=filesystem,
        device_id=device,
        rotational=rotational,
        free_bytes=free_bytes,
        ownership_capable=ownership,
        read_only=read_only,
    )


def test_valid_paths_create_the_documented_layout_and_record_devices(tmp_path: Path) -> None:
    config = _runtime_config(
        tmp_path,
        ARCHIVE_SILO_SECOND_DIR=str(tmp_path / "second archive"),
        TMP_DIR=str(tmp_path / "scratch disk"),
    )
    (tmp_path / "second archive").mkdir()
    devices: dict[Path, str] = {}

    def inspect(path: Path) -> FilesystemEvidence:
        device = devices.setdefault(path, f"8:{len(devices) + 1}")
        return _evidence(path, device=device)

    validation = validate_runtime_paths(config, inspector=inspect)
    created = create_results_layout(config, validation)

    assert validation.report.status == "ready"
    assert len({evidence.device_id for _, evidence in validation.placements}) == len(
        validation.placements
    )
    assert {path.name for path in created} >= {
        "normalized",
        "quarantine",
        "proofs",
        "exports",
        "runs",
        "services",
        "models",
        "scratch disk",
        "pgdata",
    }
    assert all(path.is_dir() for path in created)


def test_retired_proof_archive_variable_is_ignored(tmp_path: Path) -> None:
    """Leftover PROOF_ARCHIVE_DIR is an undocumented name, not a second source root."""
    leftover = tmp_path / "retired-proof"
    leftover.mkdir()
    config = _runtime_config(tmp_path, PROOF_ARCHIVE_DIR=str(leftover))

    assert "PROOF_ARCHIVE_DIR" not in dict(config.values)
    validation = validate_runtime_paths(config, inspector=_evidence)
    assert validation.report.status == "ready"
    assert all(placement.variable != "PROOF_ARCHIVE_DIR" for placement, _ in validation.placements)


@pytest.mark.parametrize("unsafe", ["archive", "checkout", "filesystem-root"])
def test_results_refuse_archive_checkout_and_dangerous_root(tmp_path: Path, unsafe: str) -> None:
    config = _runtime_config(tmp_path)
    if unsafe == "archive":
        result = config.archive_silos[0].root / "generated"
    elif unsafe == "checkout":
        result = config.project_root / "generated"
    else:
        result = Path("/")
    config = load_runtime_config(
        project_root=config.project_root,
        environment={
            "ARCHIVE_DIR": str(config.archive_silos[0].root),
            "RESULTS_DIR": str(result),
            "PGDATA_DIR": str(tmp_path / "database-two"),
        },
    )

    validation = validate_runtime_paths(config, inspector=_evidence)

    assert validation.report.status == "blocked"
    assert not (result / "normalized").exists()


def test_symlinked_results_cannot_escape_into_a_source(tmp_path: Path) -> None:
    config = _runtime_config(tmp_path)
    link = tmp_path / "results-link"
    link.symlink_to(config.archive_silos[0].root, target_is_directory=True)
    config = load_runtime_config(
        project_root=config.project_root,
        environment={
            "ARCHIVE_DIR": str(config.archive_silos[0].root),
            "RESULTS_DIR": str(link / "generated"),
            "PGDATA_DIR": str(tmp_path / "other-pg"),
        },
    )

    validation = validate_runtime_paths(config, inspector=_evidence)

    assert validation.report.status == "blocked"
    assert any("overlaps" in finding.detail for finding in validation.report.findings)


def test_database_non_overlap_includes_wal_and_tablespaces(tmp_path: Path) -> None:
    config = _runtime_config(
        tmp_path,
        PG_WAL_DIR=str(tmp_path / "pgdata/wal"),
        PG_TABLESPACE_COLD_DIR=str(tmp_path / "archive/cold"),
    )

    validation = validate_runtime_paths(config, inspector=_evidence)

    assert validation.report.status == "blocked"
    details = "\n".join(finding.detail for finding in validation.report.findings)
    assert "PG_WAL_DIR" in details
    assert "PG_TABLESPACE_COLD_DIR" in details


def test_derived_roots_may_not_alias_one_tree(tmp_path: Path) -> None:
    """Aliased derived roots would let one reset erase another root's data."""
    config = _runtime_config(
        tmp_path,
        SERVICE_STATE_DIR=str(tmp_path / "shared"),
        MODEL_CACHE_DIR=str(tmp_path / "shared/models"),
    )

    validation = validate_runtime_paths(config, inspector=_evidence)

    assert validation.report.status == "blocked"
    assert any(
        finding.name == "SERVICE_STATE_DIR" and "MODEL_CACHE_DIR" in finding.detail
        for finding in validation.report.findings
    )


def test_storage_mismatches_distinguish_refusals_from_warnings(tmp_path: Path) -> None:
    config = _runtime_config(tmp_path)

    def unsupported_database(path: Path) -> FilesystemEvidence:
        if path == config.pgdata_dir:
            return _evidence(path, filesystem="nfs", ownership=False)
        return _evidence(path)

    blocked = validate_runtime_paths(config, inspector=unsupported_database)
    assert blocked.report.status == "blocked"
    assert any("change PGDATA_DIR" in finding.detail for finding in blocked.report.findings)

    rotational = validate_runtime_paths(
        config, inspector=lambda path: _evidence(path, rotational=True)
    )
    assert rotational.report.status == "ready"

    def non_owning(path: Path) -> FilesystemEvidence:
        if path == config.service_state_dir:
            return _evidence(path, filesystem="nfs", ownership=False)
        return _evidence(path, rotational=True)

    degraded = validate_runtime_paths(config, inspector=non_owning)
    details = "\n".join(finding.detail for finding in degraded.report.findings)
    assert degraded.report.status == "degraded"
    assert all(name in details for name in ("PGDATA_DIR", "TMP_DIR", "MODEL_CACHE_DIR"))
    assert "change SERVICE_STATE_DIR" in details


def test_existing_database_root_requires_exclusive_write_ownership(tmp_path: Path) -> None:
    config = _runtime_config(tmp_path)
    config.pgdata_dir.mkdir(mode=0o777)
    config.pgdata_dir.chmod(0o777)

    validation = validate_runtime_paths(config, inspector=_evidence)

    assert validation.report.status == "blocked"
    assert any("exclusive write ownership" in item.detail for item in validation.report.findings)


def test_optional_database_roots_require_database_class_storage(tmp_path: Path) -> None:
    config = _runtime_config(
        tmp_path,
        PG_WAL_DIR=str(tmp_path / "wal"),
        PG_TABLESPACE_COLD_DIR=str(tmp_path / "cold"),
    )
    accepted = validate_runtime_paths(config, inspector=_evidence)
    assert accepted.report.status == "ready"

    def inspect(path: Path) -> FilesystemEvidence:
        if path in {config.pg_wal_dir, config.pg_tablespaces[0][1]}:
            return _evidence(path, filesystem="exfat", ownership=False)
        return _evidence(path)

    validation = validate_runtime_paths(config, inspector=inspect)
    details = "\n".join(finding.detail for finding in validation.report.findings)

    assert validation.report.status == "blocked"
    assert "change PG_WAL_DIR" in details
    assert "change PG_TABLESPACE_COLD_DIR" in details


def test_unreadable_sources_and_unwritable_output_parents_are_blocked(tmp_path: Path) -> None:
    config = _runtime_config(tmp_path)
    archive = config.archive_silos[0].root
    archive.chmod(0o000)
    unreadable = validate_runtime_paths(config, inspector=_evidence)
    archive.chmod(0o755)
    assert unreadable.report.status == "blocked"
    assert any("readable directory" in item.detail for item in unreadable.report.findings)

    locked = tmp_path / "locked"
    locked.mkdir(mode=0o555)
    locked.chmod(0o555)
    config = _runtime_config(tmp_path / "second", RESULTS_DIR=str(locked / "results"))
    unwritable = validate_runtime_paths(config, inspector=_evidence)
    locked.chmod(0o755)
    assert unwritable.report.status == "blocked"
    assert any("not writable" in item.detail for item in unwritable.report.findings)


def test_output_free_space_is_checked(tmp_path: Path) -> None:
    config = _runtime_config(tmp_path)

    def no_space(path: Path) -> FilesystemEvidence:
        return _evidence(path, free_bytes=0 if path == config.results_dir else 1_000_000)

    no_space_result = validate_runtime_paths(config, inspector=no_space)
    assert no_space_result.report.status == "blocked"
    assert any("no free space" in finding.detail for finding in no_space_result.report.findings)
