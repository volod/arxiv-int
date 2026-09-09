"""Persisted policy, archive edits, and generation refresh behavior."""

import os
from dataclasses import replace
from unittest.mock import patch

import pytest

from arxiv_int.pipeline.commands import require_frozen_context
from arxiv_int.pipeline.dag.actions import rebuild_context, update_context
from arxiv_int.pipeline.run.context import RunContext
from arxiv_int.pipeline.run.errors import ConfigDriftError, StaleUpstreamError
from arxiv_int.pipeline.run.persist import load_context, load_json, save_context, write_json
from arxiv_int.pipeline.run.snapshot import CONTENT_POLICY, METADATA_POLICY, snapshot_silos


def _load(context: RunContext) -> RunContext:
    return require_frozen_context(
        context.runs_dir, context.run_id, project_root=context.project_root, environment={}
    )


@pytest.mark.parametrize(
    "change", ["edit", "same-size", "replace", "add", "remove", "rename", "mode", "missing"]
)
def test_archive_drift_refuses_frozen_context(frozen_run: RunContext, change: str) -> None:
    root = frozen_run.silos[0].root
    path = root / "doc.txt"
    before = path.stat()
    if change == "edit":
        path.write_bytes(b"longer content")
    elif change == "same-size":
        path.write_bytes(b"two")
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    elif change == "replace":
        replacement = root / "replacement"
        replacement.write_bytes(b"two")
        os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
        replacement.replace(path)
    elif change == "add":
        (root / "new").write_bytes(b"new")
    elif change == "remove":
        path.unlink()
    elif change == "rename":
        path.rename(root / "renamed")
    elif change == "mode":
        path.chmod(0o000)
    else:
        root.rename(root.with_name("moved"))
    with pytest.raises(StaleUpstreamError, match="archive snapshot changed"):
        _load(frozen_run)


def test_reads_do_not_cause_drift(frozen_run: RunContext) -> None:
    assert (frozen_run.silos[0].root / "doc.txt").read_bytes() == b"one"
    assert _load(frozen_run) == frozen_run


def test_configuration_drift_still_refuses_before_source_scan(frozen_run: RunContext) -> None:
    with (
        patch("arxiv_int.pipeline.commands.metadata_snapshot", side_effect=AssertionError),
        pytest.raises(ConfigDriftError),
    ):
        require_frozen_context(
            frozen_run.runs_dir,
            frozen_run.run_id,
            project_root=frozen_run.project_root,
            environment={"LOG_FORMAT": "jsonl"},
        )


def test_update_refreshes_both_snapshots_and_rebuild_preserves_them(frozen_run: RunContext) -> None:
    (frozen_run.silos[0].root / "doc.txt").write_bytes(b"two")
    updated = update_context(frozen_run)
    assert updated.generation_id != frozen_run.generation_id
    assert updated.source_snapshot != frozen_run.source_snapshot
    assert updated.source_metadata_snapshot != frozen_run.source_metadata_snapshot
    save_context(updated)
    assert _load(updated) == updated
    rebuilt = rebuild_context(updated)
    assert rebuilt.generation_id != updated.generation_id
    assert rebuilt.source_snapshot == updated.source_snapshot
    assert rebuilt.source_metadata_snapshot == updated.source_metadata_snapshot
    save_context(rebuilt)
    assert _load(rebuilt) == rebuilt


def test_legacy_context_retains_full_content_checks(frozen_run: RunContext) -> None:
    path = save_context(frozen_run)
    payload = load_json(path)
    del payload["source_drift_policy"]
    del payload["source_metadata_snapshot"]
    write_json(path, payload)
    with patch("arxiv_int.pipeline.commands.snapshot_silos", wraps=snapshot_silos) as reader:
        legacy = _load(frozen_run)
        reader.assert_called_once_with(frozen_run.silos)
    assert legacy.source_drift_policy == CONTENT_POLICY
    (legacy.silos[0].root / "doc.txt").write_bytes(b"changed")
    with pytest.raises(StaleUpstreamError):
        _load(legacy)
    updated = update_context(legacy)
    assert updated.source_drift_policy == METADATA_POLICY
    save_context(updated)
    assert _load(updated) == updated


@pytest.mark.parametrize(
    "policy,metadata",
    [("unknown", "hash"), (METADATA_POLICY, None), (METADATA_POLICY, ""), (CONTENT_POLICY, "hash")],
)
def test_invalid_policy_evidence_refuses_load(
    frozen_run: RunContext, policy: str, metadata: str | None
) -> None:
    path = save_context(frozen_run)
    payload = load_json(path)
    payload.update(source_drift_policy=policy, source_metadata_snapshot=metadata)
    write_json(path, payload)
    with pytest.raises(ValueError):
        load_context(frozen_run.runs_dir, frozen_run.run_id)


def test_missing_policy_cannot_silently_downgrade_metadata_context(frozen_run: RunContext) -> None:
    path = save_context(frozen_run)
    payload = load_json(path)
    del payload["source_drift_policy"]
    write_json(path, payload)
    with pytest.raises(ValueError):
        load_context(frozen_run.runs_dir, frozen_run.run_id)


def test_noop_update_keeps_content_identity(frozen_run: RunContext) -> None:
    updated = update_context(frozen_run)
    assert (
        replace(updated, run_id=frozen_run.run_id, generation_id=frozen_run.generation_id)
        == frozen_run
    )
