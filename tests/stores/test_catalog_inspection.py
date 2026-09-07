"""Setup reuse must retain physical store checks at the applied revision."""

from dataclasses import replace
from unittest.mock import MagicMock

import pytest

from arxiv_int.stores.postgres import apply
from tests.stores.test_canonical_schema_apply import _complete_catalog, _root


@pytest.mark.parametrize("at_applied_revision", [False, True])
def test_missing_partitions_refuse_catalog_reuse(
    monkeypatch: pytest.MonkeyPatch, at_applied_revision: bool
) -> None:
    monkeypatch.setattr(apply, "_engine", lambda _url: MagicMock())
    monkeypatch.setattr(
        apply, "inspect_store", lambda _connection: replace(_complete_catalog(), partitioned=())
    )
    monkeypatch.setattr(apply, "compare_live_catalog", lambda *_args: [])
    monkeypatch.setattr(apply, "catalog_boundary_findings", lambda *_args: [])
    monkeypatch.setattr(apply, "capture_catalog", lambda *_args: {})
    findings, _, _ = apply.inspect_and_compare(
        _root(), "postgresql://fixture", at_applied_revision=at_applied_revision
    )
    assert any("missing HASH parents" in item for item in findings)
