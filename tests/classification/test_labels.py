"""Gold label resolution, deterministic leakage-free splits, and scoring compatibility."""

from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from arxiv_int.classification.labels import (
    LabelError,
    assign_splits,
    evaluation_item_row,
    label_row,
    resolve_label,
    split_ledger,
)
from arxiv_int.classification.vocabulary.build import build_scheme
from arxiv_int.classification.vocabulary.model import Scheme
from arxiv_int.classification.vocabulary.policy import SchemePolicy, load_scheme_policy
from arxiv_int.classification.vocabulary.snapshot import load_snapshot, write_snapshot
from arxiv_int.evaluation.scoring.accuracy import score_classification
from tests.classification._fixtures import write_project


@pytest.fixture(name="policy")
def policy_fixture(tmp_path: Path) -> SchemePolicy:
    return load_scheme_policy(write_project(tmp_path / "project"))


@pytest.fixture(name="scheme")
def scheme_fixture(policy: SchemePolicy, tmp_path: Path) -> Scheme:
    write_snapshot(tmp_path / "scheme", build_scheme(policy, run_id="r1"))
    return load_snapshot(tmp_path / "scheme").scheme


def label(item: str, **fields: Any) -> dict[str, Any]:
    return {"gold_ref": f"doc-{item}", "item_id": item, **fields}


def test_primary_class_resolves_with_its_path(scheme: Scheme, policy: SchemePolicy) -> None:
    gold = resolve_label(
        label("a", primary="tax:01.02.01", alternates=["tax:02.01"]), scheme, policy
    )
    assert gold.path == ("tax:01", "tax:01.02", "tax:01.02.01") and gold.stratum == "tax:01"
    row = label_row(gold, "subjects-x")
    assert score_classification(row, row).exact == 1.0


def test_deep_code_is_truncated_not_invented(scheme: Scheme, policy: SchemePolicy) -> None:
    gold = resolve_label(label("a", primary_code="01.02.01.07"), scheme, policy)
    assert gold.primary == "tax:01.02.01" and gold.truncated_from == "01.02.01.07"
    with pytest.raises(LabelError):
        resolve_label(label("b", primary_code="09.01"), scheme, policy)


def test_exceptional_outcome_scores_as_exceptional(scheme: Scheme, policy: SchemePolicy) -> None:
    gold = label_row(resolve_label(label("a", primary="unreadable"), scheme, policy), "s")
    other = {"path": ["unclassified"], "primary": "unclassified"}
    assert gold["path"] == ["unreadable"]
    assert score_classification(gold, gold).exceptional == 1.0
    assert score_classification(gold, other).exceptional == 0.0


@pytest.mark.parametrize(
    "fields",
    [
        {"primary": "tax:09"},
        {"primary": "tax:01", "primary_code": "01"},
        {},
        {"primary": "tax:01.01", "alternates": ["tax:01.01"]},
        {"primary": "tax:01.01", "alternates": ["unclassified"]},
        {"primary": "unclassified", "alternates": ["tax:01.01"]},
        {"primary": "tax:01.01", "split": "holdout"},
    ],
)
def test_invalid_labels_are_refused(
    scheme: Scheme, policy: SchemePolicy, fields: dict[str, Any]
) -> None:
    with pytest.raises(LabelError):
        resolve_label(label("a", **fields), scheme, policy)


def test_splits_are_deterministic_balanced_and_keep_duplicates_together(
    scheme: Scheme, policy: SchemePolicy
) -> None:
    records = [label(f"i{n}", primary="tax:01.01.01" if n % 2 else "tax:02.02") for n in range(200)]
    records.append(label("dup-a", primary="tax:01.01.01", content_sha256="same"))
    records.append(label("dup-b", primary="tax:01.02.02", content_sha256="same"))
    labels = [resolve_label(record, scheme, policy) for record in records]
    first = assign_splits(labels, policy)
    assert first == assign_splits(labels, policy)
    by_item = {item.item_id: item.split for item in first}
    assert by_item["dup-a"] == by_item["dup-b"]
    counts = Counter(item.split for item in first)
    assert abs(counts["test"] - 101) <= 2 and abs(counts["calibration"] - 40) <= 2
    ledger = split_ledger(first, policy)
    assert ledger["items"] == 202 and ledger["groups"] == 201
    row = evaluation_item_row(first[0], "gold-1", "r1")
    assert row["evaluation_item_id"] == "gold-1:i0" and row["item_kind"] == "classification"


def test_conflicting_declared_splits_or_duplicate_items_fail(
    scheme: Scheme, policy: SchemePolicy
) -> None:
    conflict = [
        resolve_label(
            label("a", primary="tax:01", content_sha256="x", split="test"), scheme, policy
        ),
        resolve_label(
            label("b", primary="tax:01", content_sha256="x", split="development"), scheme, policy
        ),
    ]
    with pytest.raises(LabelError):
        assign_splits(conflict, policy)
    same = resolve_label(label("a", primary="tax:01"), scheme, policy)
    with pytest.raises(LabelError):
        assign_splits([same, same], policy)
