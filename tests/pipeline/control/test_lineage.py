"""Owned fingerprint changes mark exactly the reachable lineage closure stale."""

from arxiv_int.pipeline.control.fingerprints import reuse_key
from arxiv_int.pipeline.control.lineage import (
    LineageEdge,
    keys_matching_owned_change,
    stale_closure,
)
from tests.pipeline.control.identities import identity


def test_stale_closure_includes_only_descendants() -> None:
    producer = reuse_key(identity(shard_id="p"))
    child = reuse_key(identity(shard_id="c"))
    cousin = reuse_key(identity(shard_id="x"))
    edges = (
        LineageEdge(producer, child),
        LineageEdge(reuse_key(identity(shard_id="other")), cousin),
    )
    assert stale_closure({producer}, edges) == frozenset({producer, child})
    assert cousin not in stale_closure({producer}, edges)


def test_owned_fingerprint_selects_matching_identities_only() -> None:
    left = identity(shard_id="left")
    right = identity(shard_id="right", code_fingerprint="code_fingerprint-v2")
    identities = {reuse_key(left): left, reuse_key(right): right}
    matched = keys_matching_owned_change(identities, "code_fingerprint", "code_fingerprint-v1")
    assert matched == frozenset({reuse_key(left)})
