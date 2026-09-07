"""Shared identities for run-ledger tests."""

from arxiv_int.pipeline.control.fingerprints import OWNED_FINGERPRINT_FIELDS, ReuseIdentity
from arxiv_int.pipeline.control.quality import QualityCheck


def owned_fingerprints(**overrides: str) -> dict[str, str]:
    values = {name: f"{name}-v1" for name in OWNED_FINGERPRINT_FIELDS}
    values.update(overrides)
    return values


def identity(*, shard_id: str = "shard-a", **owned: str) -> ReuseIdentity:
    return ReuseIdentity(
        stage="normalize",
        stage_version="1",
        shard_id=shard_id,
        parameters={"bucket": "0"},
        input_hashes=("hash-a",),
        upstream_manifest_ids=(),
        owned=owned_fingerprints(**owned),
    )


def passing_checks() -> tuple[QualityCheck, ...]:
    return (
        QualityCheck("global.row_count", "pass", "global", "error", True),
        QualityCheck("batch.not_null", "pass", "batch", "error", True),
    )
