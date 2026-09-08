"""Deterministic reuse keys from stage-owned fingerprints and quality identities."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from arxiv_int.contracts.generate.normalize import sha256_text
from arxiv_int.interfaces.tokens import freeze_str_mapping, require_token

OWNED_FINGERPRINT_FIELDS: tuple[str, ...] = (
    "code_fingerprint",
    "dependency_fingerprint",
    "contract_fingerprint",
    "schema_fingerprint",
    "tool_fingerprint",
    "model_fingerprint",
    "prompt_fingerprint",
    "configuration_fingerprint",
    "validation_catalog_fingerprint",
    "dbt_model_fingerprint",
    "dbt_input_fingerprint",
    "dbt_rule_fingerprint",
)


@dataclass(frozen=True, slots=True)
class ReuseIdentity:
    """Everything that must match before a successful shard is reusable."""

    stage: str
    stage_version: str
    shard_id: str
    parameters: Mapping[str, str]
    input_hashes: tuple[str, ...]
    upstream_manifest_ids: tuple[str, ...]
    owned: Mapping[str, str]

    def __post_init__(self) -> None:
        require_token(self.stage, "stage")
        require_token(self.stage_version, "stage_version")
        require_token(self.shard_id, "shard_id")
        object.__setattr__(self, "parameters", freeze_str_mapping(self.parameters))
        _require_tokens(self.input_hashes, "input_hashes")
        _require_tokens(self.upstream_manifest_ids, "upstream_manifest_ids")
        owned = freeze_str_mapping(self.owned)
        missing = [name for name in OWNED_FINGERPRINT_FIELDS if name not in owned]
        if missing:
            raise ValueError(f"reuse identity is missing owned fingerprints: {', '.join(missing)}")
        extra = sorted(set(owned) - set(OWNED_FINGERPRINT_FIELDS))
        if extra:
            raise ValueError(f"reuse identity has unknown owned fingerprints: {', '.join(extra)}")
        for name, value in owned.items():
            require_token(value, name)
        object.__setattr__(self, "owned", owned)


def reuse_key(identity: ReuseIdentity) -> str:
    """Return a stable SHA-256 reuse key for one shard identity."""
    parts = [
        identity.stage,
        identity.stage_version,
        identity.shard_id,
        *[f"{key}={value}" for key, value in sorted(identity.parameters.items())],
        "inputs:" + ",".join(identity.input_hashes),
        "upstream:" + ",".join(identity.upstream_manifest_ids),
        *[f"{name}={identity.owned[name]}" for name in OWNED_FINGERPRINT_FIELDS],
    ]
    return sha256_text("|".join(parts))


def _require_tokens(values: Sequence[str], field: str) -> None:
    for index, value in enumerate(values):
        require_token(value, f"{field}[{index}]")
