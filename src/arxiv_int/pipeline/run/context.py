"""Frozen run context: unique id, profile, configuration fingerprint, and silos."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from arxiv_int.contracts.generate.normalize import normalize_json, sha256_text
from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.interfaces.tokens import freeze_str_mapping, require_token
from arxiv_int.pipeline.inventory.snapshot import INVENTORY_METADATA_POLICY
from arxiv_int.pipeline.run.snapshot import CONTENT_POLICY, METADATA_POLICY
from arxiv_int.pipeline.run.snapshot import snapshot_silos as snapshot_silos

_SENSITIVE_MARKERS = ("PASSWORD", "SECRET", "TOKEN", "DATABASE_URL", "CREDENTIAL")


@dataclass(frozen=True, slots=True)
class RunContext:
    """Immutable requested configuration for one generation."""

    run_id: str
    generation_id: str
    profile: str
    config_fingerprint: str
    source_snapshot: str
    silos: tuple[SiloRoot, ...]
    results_dir: Path
    runs_dir: Path
    project_root: Path
    secret_free: Mapping[str, str]
    parameters: Mapping[str, str]
    from_stage: str | None = None
    to_stage: str | None = None
    source_drift_policy: str = CONTENT_POLICY
    source_metadata_snapshot: str | None = None

    def __post_init__(self) -> None:
        require_token(self.run_id, "run_id")
        require_token(self.generation_id, "generation_id")
        require_token(self.profile, "profile")
        require_token(self.config_fingerprint, "config_fingerprint")
        require_token(self.source_snapshot, "source_snapshot")
        if self.source_drift_policy not in {
            CONTENT_POLICY,
            METADATA_POLICY,
            INVENTORY_METADATA_POLICY,
        }:
            raise ValueError("unsupported source drift policy")
        if self.source_drift_policy in {METADATA_POLICY, INVENTORY_METADATA_POLICY}:
            if self.source_metadata_snapshot is None:
                raise ValueError("stat-v1 requires a source metadata snapshot")
            require_token(self.source_metadata_snapshot, "source_metadata_snapshot")
        elif self.source_metadata_snapshot is not None:
            raise ValueError("full-content-v1 cannot carry a source metadata snapshot")
        object.__setattr__(self, "secret_free", freeze_str_mapping(self.secret_free))
        object.__setattr__(self, "parameters", freeze_str_mapping(self.parameters))


def allocate_run_id() -> str:
    """Return a unique run id that is never the developer ``local`` fallback."""
    return f"run-{uuid4().hex}"


def secret_free_values(values: Mapping[str, str]) -> dict[str, str]:
    """Drop credential-bearing keys from frozen configuration evidence."""
    return {
        key: value
        for key, value in values.items()
        if not any(marker in key.upper() for marker in _SENSITIVE_MARKERS)
    }


def config_fingerprint(profile: str, secret_free: Mapping[str, str]) -> str:
    """Fingerprint profile and secret-free roots; archive bytes are a separate snapshot."""
    payload = {"profile": profile, "values": dict(sorted(secret_free.items()))}
    return sha256_text(normalize_json(payload))
