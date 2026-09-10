"""Proofs cannot infer resource measurements from a missing or empty log."""

import json

import pytest

from arxiv_int.evaluation.evaluate.errors import ProofIntegrityError
from arxiv_int.evaluation.proof.corpus_artifacts import STAGES
from arxiv_int.evaluation.proof.corpus_metrics import resource_summary


def _samples() -> list[dict[str, object]]:
    return [
        {
            "stage": stage,
            "worker_state": "completed",
            "elapsed_seconds": 2,
            "cpu_pct": 20,
            "ram_available_gib": 10,
            "disk_free_gib": 100,
        }
        for stage in STAGES
    ]


def _encode(rows: list[dict[str, object]]) -> bytes:
    return "\n".join(json.dumps(row) for row in rows).encode("ascii")


def test_resource_summary_requires_complete_measured_stage_history() -> None:
    assert resource_summary(_encode(_samples()))["extract"]["max_elapsed_seconds"] == 2
    with pytest.raises(ProofIntegrityError, match="missing resource"):
        resource_summary(_encode(_samples()[:-1]))


@pytest.mark.parametrize("value", (None, -1, float("nan"), True))
def test_missing_or_invalid_measurement_refuses(value: object) -> None:
    rows = _samples()
    rows[0]["cpu_pct"] = value
    with pytest.raises(ProofIntegrityError, match="invalid resource"):
        resource_summary(_encode(rows))
