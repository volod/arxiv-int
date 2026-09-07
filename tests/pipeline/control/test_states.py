"""State-machine tests for ledger status transitions and retry classes."""

import pytest

from arxiv_int.pipeline.control.states import (
    LEASE_TRANSITIONS,
    LEDGER_TRANSITIONS,
    MANIFEST_TRANSITIONS,
    IllegalTransitionError,
    as_lease_status,
    as_shard_status,
    can_retry,
    classify_failure,
    require_transition,
)


@pytest.mark.parametrize(
    ("kind", "current", "target"),
    [
        ("run", "pending", "running"),
        ("stage", "running", "succeeded"),
        ("shard", "succeeded", "stale"),
        ("shard", "running", "stale"),
        ("lease", "acquired", "expired"),
        ("manifest", "staging", "accepted"),
    ],
)
def test_legal_transitions_are_accepted(kind: str, current: str, target: str) -> None:
    require_transition(kind, current, target)


@pytest.mark.parametrize(
    ("kind", "table"),
    [
        ("run", LEDGER_TRANSITIONS),
        ("lease", LEASE_TRANSITIONS),
        ("manifest", MANIFEST_TRANSITIONS),
    ],
)
def test_illegal_transitions_are_rejected(kind: str, table: dict[str, frozenset[str]]) -> None:
    statuses = set(table)
    for current in statuses:
        for target in statuses:
            if current == target or target in table[current]:
                continue
            with pytest.raises(IllegalTransitionError, match="illegal"):
                require_transition(kind, current, target)
        for target in table[current]:
            require_transition(kind, current, target)


def test_pruned_and_released_rows_cannot_move() -> None:
    with pytest.raises(IllegalTransitionError):
        require_transition("shard", "pruned", "succeeded")
    with pytest.raises(IllegalTransitionError):
        require_transition("lease", "released", "acquired")
    with pytest.raises(IllegalTransitionError):
        require_transition("manifest", "accepted", "staging")


def test_retry_taxonomy_bounds_transient_attempts() -> None:
    assert classify_failure("timeout") == "transient"
    assert classify_failure("validation") == "permanent"
    assert can_retry("transient", 1, 3)
    assert can_retry("transient", 2, 3)
    assert not can_retry("transient", 3, 3)
    assert not can_retry("permanent", 1, 3)
    with pytest.raises(ValueError, match="unknown failure"):
        classify_failure("disk-full")


def test_stored_status_tokens_are_validated() -> None:
    assert as_shard_status("succeeded") == "succeeded"
    assert as_lease_status("expired") == "expired"
    with pytest.raises(ValueError, match="unknown shard status"):
        as_shard_status("done")
    with pytest.raises(ValueError, match="unknown lease status"):
        as_lease_status("open")
