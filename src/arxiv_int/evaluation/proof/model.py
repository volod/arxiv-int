"""Typed proof manifests and the stage-to-validator capability registry."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from arxiv_int.evaluation.bundles.manifest import canonical_json, identity_text
from arxiv_int.evaluation.evaluate.errors import ProofIntegrityError, ProofUnknownCapabilityError
from arxiv_int.evaluation.evaluate.paths import proof_config_path

PROOF_SCHEMA_VERSION = 1
VALIDATOR_BUNDLE = "evaluation-bundle"
VALIDATOR_CHECKSUMS = "artifact-checksums"
VALIDATOR_SPLIT = "split-leakage"
VALIDATOR_LEDGER = "item-ledger"
VALIDATOR_STAGE = "stage-validation"


@dataclass(frozen=True, slots=True)
class CapabilityProofTarget:
    """One registered capability and the stages/validators it must publish."""

    capability_id: str
    usable_stages: tuple[str, ...]
    required_validators: tuple[str, ...]
    proof_kind: str


@dataclass(frozen=True, slots=True)
class ProofManifest:
    """Immutable proof identity published under RESULTS_DIR/proofs."""

    schema_version: int
    capability_id: str
    proof_id: str
    run_id: str
    data_class: str
    verdict: str
    fingerprints: Mapping[str, str]
    stages: Mapping[str, str]
    validators: Mapping[str, str]
    artifacts: Mapping[str, Mapping[str, int | str]]

    def as_json_dict(self) -> dict[str, object]:
        """Return the canonical proof manifest object."""
        return {
            "artifacts": {name: dict(record) for name, record in sorted(self.artifacts.items())},
            "capability_id": self.capability_id,
            "data_class": self.data_class,
            "fingerprints": dict(self.fingerprints),
            "proof_id": self.proof_id,
            "run_id": self.run_id,
            "schema_version": self.schema_version,
            "stages": dict(self.stages),
            "validators": dict(self.validators),
            "verdict": self.verdict,
        }


def capability_registry_document() -> dict[str, object]:
    """Return the committed capability-to-validator registry."""
    return {
        "capabilities": {
            "anomaly-analysis": _target(["anomalies"], [VALIDATOR_CHECKSUMS, VALIDATOR_STAGE]),
            "archive-classification": _target(["classify"], [VALIDATOR_CHECKSUMS, VALIDATOR_STAGE]),
            "corpus-foundation": _target(
                ["inventory", "extract", "normalize", "dedupe", "chunk"],
                [VALIDATOR_CHECKSUMS, VALIDATOR_STAGE],
            ),
            "discovery-visualization": _target(
                ["catalogs", "report"], [VALIDATOR_CHECKSUMS, VALIDATOR_STAGE]
            ),
            "domain-investigation-artifacts": _target(
                ["domain-artifacts"], [VALIDATOR_CHECKSUMS, VALIDATOR_STAGE]
            ),
            "evaluation-evidence": _target(
                ["evaluate", "report"], [VALIDATOR_BUNDLE, VALIDATOR_CHECKSUMS, VALIDATOR_STAGE]
            ),
            "evaluation-foundation": _target(
                ["evaluate"],
                [VALIDATOR_BUNDLE, VALIDATOR_SPLIT, VALIDATOR_LEDGER],
                proof_kind="fixtures",
            ),
            "identity-ontology-graph": _target(
                ["entities", "ontology", "graph"], [VALIDATOR_CHECKSUMS, VALIDATOR_STAGE]
            ),
            "knowledge-extraction": _target(
                ["facts", "validate-facts"], [VALIDATOR_CHECKSUMS, VALIDATOR_STAGE]
            ),
            "lexical-retrieval": _target(["load-lexical"], [VALIDATOR_CHECKSUMS, VALIDATOR_STAGE]),
            "pipeline-control": _target(["preflight"], [VALIDATOR_CHECKSUMS, VALIDATOR_STAGE]),
            "russian-nlp": _target(["nlp"], [VALIDATOR_CHECKSUMS, VALIDATOR_STAGE]),
            "semantic-retrieval": _target(
                ["embed", "load-vector"], [VALIDATOR_CHECKSUMS, VALIDATOR_STAGE]
            ),
        },
        "schema_version": PROOF_SCHEMA_VERSION,
    }


def load_capability_registry(project_root: Path) -> dict[str, CapabilityProofTarget]:
    """Load the committed registry or raise if it is missing."""
    path = proof_config_path(project_root)
    payload = _read_registry(path)
    capabilities = payload.get("capabilities")
    if payload.get("schema_version") != PROOF_SCHEMA_VERSION or not isinstance(capabilities, dict):
        raise ProofIntegrityError("proof capability registry is missing or malformed")
    parsed: dict[str, CapabilityProofTarget] = {}
    for capability_id, record in capabilities.items():
        parsed[str(capability_id)] = _parse_target(str(capability_id), record)
    return parsed


def require_capability(
    registry: Mapping[str, CapabilityProofTarget], capability_id: str
) -> CapabilityProofTarget:
    """Return one registered target or name unknown capabilities."""
    target = registry.get(capability_id)
    if target is None:
        known = ", ".join(sorted(registry))
        raise ProofUnknownCapabilityError(
            f"unknown proof capability {capability_id!r}; registered capabilities are {known}"
        )
    return target


def parse_proof_manifest(payload: Mapping[str, object]) -> ProofManifest:
    """Type-check a proof manifest object."""
    required = (
        "schema_version",
        "capability_id",
        "proof_id",
        "run_id",
        "data_class",
        "verdict",
        "fingerprints",
        "stages",
        "validators",
        "artifacts",
    )
    missing = [name for name in required if name not in payload]
    if missing or payload.get("schema_version") != PROOF_SCHEMA_VERSION:
        raise ProofIntegrityError("proof manifest identities are missing or malformed")
    artifacts = payload["artifacts"]
    if not isinstance(artifacts, dict) or not artifacts:
        raise ProofIntegrityError("proof manifest is missing artifact checksums")
    return ProofManifest(
        schema_version=PROOF_SCHEMA_VERSION,
        capability_id=identity_text("capability_id", payload["capability_id"]),
        proof_id=identity_text("proof_id", payload["proof_id"]),
        run_id=identity_text("run_id", payload["run_id"]),
        data_class=identity_text("data_class", payload["data_class"]),
        verdict=identity_text("verdict", payload["verdict"]),
        fingerprints=_string_map("fingerprints", payload["fingerprints"]),
        stages=_string_map("stages", payload["stages"]),
        validators=_string_map("validators", payload["validators"]),
        artifacts=_artifact_map(artifacts),
    )


def _target(
    stages: list[str], validators: list[str], *, proof_kind: str = "provided-archive"
) -> dict[str, object]:
    return {
        "proof_kind": proof_kind,
        "required_validators": validators,
        "usable_stages": stages,
    }


def _parse_target(capability_id: str, record: object) -> CapabilityProofTarget:
    if not isinstance(record, dict):
        raise ProofIntegrityError(f"capability {capability_id} is malformed")
    stages = record.get("usable_stages")
    validators = record.get("required_validators")
    kind = record.get("proof_kind")
    if (
        not isinstance(stages, list)
        or not isinstance(validators, list)
        or not isinstance(kind, str)
    ):
        raise ProofIntegrityError(f"capability {capability_id} is malformed")
    return CapabilityProofTarget(
        capability_id,
        tuple(str(item) for item in stages),
        tuple(str(item) for item in validators),
        kind,
    )


def _string_map(field: str, value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ProofIntegrityError(f"proof manifest {field} is missing or malformed")
    return {
        identity_text(f"{field} key", key): identity_text(f"{field}[{key}]", item)
        for key, item in value.items()
    }


def _artifact_map(value: dict[str, Any]) -> dict[str, dict[str, int | str]]:
    registry: dict[str, dict[str, int | str]] = {}
    for name, record in value.items():
        if not isinstance(record, dict) or "sha256" not in record or "bytes" not in record:
            raise ProofIntegrityError(f"proof artifact {name} is missing a checksum")
        digest = record["sha256"]
        size = record["bytes"]
        if not isinstance(digest, str) or not isinstance(size, int) or size < 0:
            raise ProofIntegrityError(f"proof artifact {name} is missing a checksum")
        registry[str(name)] = {"bytes": size, "sha256": digest}
    return registry


def _read_registry(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise ProofIntegrityError(f"missing proof capability registry {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ProofIntegrityError("proof capability registry is not an object")
    expected = canonical_json(capability_registry_document())
    if path.read_bytes() != expected:
        raise ProofIntegrityError("proof capability registry drifted from generation")
    return payload
