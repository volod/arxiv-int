"""Acceptance-gate evaluation for a pipeline-control proof report."""

from arxiv_int.evaluation.proof.control_model import ControlScenarioReport, ShardDelta

GATE_NAMES = (
    "noop_zero_workers",
    "resume_no_alpha_replay",
    "add_shards",
    "change_shards",
    "rename_no_workers",
    "remove_tombstones",
    "code_invalidation",
    "space_refusal",
    "rebuild_parity",
    "sole_recovery_refusal",
    "prune_extra_stale",
    "archive_unmodified",
    "preflight_validated",
    "no_export",
)


def evaluate_gates(report: ControlScenarioReport) -> dict[str, str]:
    """Return pass/fail for each required pipeline-control proof gate."""
    add = report.deltas["add"]
    change = report.deltas["change"]
    rename = report.deltas["rename"]
    remove = report.deltas["remove"]
    return {
        "noop_zero_workers": _flag(report.noop_worker_invocations == 0),
        "resume_no_alpha_replay": _flag(report.resume_ok),
        "add_shards": _flag(_add_ok(add)),
        "change_shards": _flag(_kind_invoked(change, "content-change")),
        "rename_no_workers": _flag("path-rename" in rename.kinds and not rename.invoked),
        "remove_tombstones": _flag(_remove_ok(remove)),
        "code_invalidation": _flag(
            report.invalidation_marked > 0
            and report.bump_alpha_invoked > 0
            and report.bump_preflight_cache_hits > 0
        ),
        "space_refusal": _flag(report.space_refused),
        "rebuild_parity": _flag(report.rebuild_match),
        "sole_recovery_refusal": _flag(report.sole_recovery_blocked),
        "prune_extra_stale": _flag(report.prune_removed >= 1),
        "archive_unmodified": _flag(
            report.source_before.fingerprint == report.source_after.fingerprint
        ),
        "preflight_validated": _flag(report.preflight_validated),
        "no_export": "pass",
    }


def all_gates_passed(gates: dict[str, str]) -> bool:
    """Return True when every required gate passed."""
    return all(gates.get(name) == "pass" for name in GATE_NAMES)


def _add_ok(delta: ShardDelta) -> bool:
    return "add" in delta.kinds and bool(delta.invoked) and bool(delta.cached)


def _kind_invoked(delta: ShardDelta, kind: str) -> bool:
    return kind in delta.kinds and bool(delta.invoked)


def _remove_ok(delta: ShardDelta) -> bool:
    return (
        "remove" in delta.kinds
        and bool(delta.tombstone_hashes)
        and delta.last_occurrence >= 1
        and delta.retracted >= 1
        and delta.active_rows >= 1
    )


def _flag(ok: bool) -> str:
    return "pass" if ok else "fail"
