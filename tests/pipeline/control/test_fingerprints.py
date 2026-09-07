"""Reuse-key stability for owned fingerprint identities."""

import pytest

from arxiv_int.pipeline.control.fingerprints import reuse_key
from tests.pipeline.control.identities import identity


def test_reuse_key_is_stable_and_sensitive_to_owned_code() -> None:
    left = reuse_key(identity())
    again = reuse_key(identity())
    changed = reuse_key(identity(code_fingerprint="code_fingerprint-v2"))
    assert left == again
    assert left != changed


def test_reuse_identity_refuses_missing_owned_fields() -> None:
    with pytest.raises(ValueError, match="missing owned fingerprints"):
        identity().__class__(
            stage="normalize",
            stage_version="1",
            shard_id="s",
            parameters={},
            input_hashes=(),
            upstream_manifest_ids=(),
            owned={"code_fingerprint": "x"},
        )
