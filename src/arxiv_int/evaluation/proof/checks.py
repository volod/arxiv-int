"""Proof freshness, checksum, usable-stage, and repository-summary redaction."""

import os
import re
from collections.abc import Mapping
from pathlib import Path

from arxiv_int.evaluation.evaluate.errors import (
    ProofIntegrityError,
    ProofRedactionError,
    ProofStaleError,
)
from arxiv_int.evaluation.evaluate.run import code_fingerprint
from arxiv_int.evaluation.fixtures.kinds import SYNTHETIC_IDENTITY_TOKENS
from arxiv_int.evaluation.proof.model import (
    VALIDATOR_STAGE,
    CapabilityProofTarget,
    ProofManifest,
    parse_proof_manifest,
)

_PATH_MARKERS = ("/home/", "/Users/", "C:\\", "/mnt/", "/opt/")
_ENV_PATH_VARS = ("ARCHIVE_DIR", "RESULTS_DIR", "RUNS_DIR", "PGDATA_DIR", "DATA_DIR")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def current_fingerprints(project_root: Path, fixture_fingerprint: str) -> dict[str, str]:
    """Return the live code and fixture fingerprints a proof must match."""
    return {"code": code_fingerprint(project_root), "fixtures": fixture_fingerprint}


def refuse_stale_fingerprints(manifest: ProofManifest, expected: Mapping[str, str]) -> None:
    """Reject a proof whose recorded inputs no longer match."""
    for name, digest in expected.items():
        recorded = manifest.fingerprints.get(name)
        if recorded != digest:
            raise ProofStaleError(f"proof fingerprint {name} is stale")


def refuse_missing_checksums(manifest: ProofManifest) -> None:
    """Reject artifacts that lack a sha256 digest or byte count."""
    if not manifest.artifacts:
        raise ProofIntegrityError("proof manifest is missing artifact checksums")
    for name, record in manifest.artifacts.items():
        digest = record.get("sha256")
        size = record.get("bytes")
        if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
            raise ProofIntegrityError(f"proof artifact {name} is missing a checksum")
        if not isinstance(size, int) or size < 0:
            raise ProofIntegrityError(f"proof artifact {name} is missing a checksum")


def refuse_unvalidated_stages(manifest: ProofManifest, target: CapabilityProofTarget) -> None:
    """Reject a capability proof that skipped a usable stage validator."""
    for stage in target.usable_stages:
        status = manifest.stages.get(stage)
        if status not in {"validated", "empty"}:
            raise ProofIntegrityError(f"usable stage {stage} is unvalidated")
        if (
            status == "validated"
            and VALIDATOR_STAGE in target.required_validators
            and manifest.validators.get(f"stage:{stage}") != "pass"
        ):
            raise ProofIntegrityError(f"usable stage {stage} is unvalidated")
    for validator in target.required_validators:
        if manifest.validators.get(validator) != "pass":
            raise ProofIntegrityError(f"required validator {validator} did not pass")


def redact_summary_text(text: str) -> str:
    """Replace configured roots and secret-like values in a repository summary."""
    redacted = text
    for name in _ENV_PATH_VARS:
        value = os.environ.get(name, "").strip()
        if value:
            redacted = redacted.replace(value, f"${name}")
    for marker in _PATH_MARKERS:
        if marker in redacted:
            raise ProofRedactionError("repository summary contains a private path")
    if len(redacted) > 4000:
        return redacted[:4000] + "..."
    return redacted


def refuse_corpus_leak(text: str, forbidden: Mapping[str, str] | None = None) -> None:
    """Refuse unobfuscated identity or source strings in a Git-bound summary."""
    tokens = dict(SYNTHETIC_IDENTITY_TOKENS)
    tokens.update(forbidden or {})
    for label, original in tokens.items():
        if original and original in text:
            raise ProofRedactionError(f"repository summary contains unobfuscated {label}")


def refuse_proof_payloads(payloads: Mapping[str, str]) -> None:
    """Refuse identity tokens and private paths in Git-bound proof payloads."""
    for name, text in payloads.items():
        if name == "identities.json" or name.endswith("/identities.json"):
            raise ProofRedactionError("proof directory contains identities.json")
        refuse_corpus_leak(text)
        redact_summary_text(text)


def refuse_proof_tree_leaks(directory: Path) -> None:
    """Refuse identity catalogs, leaked text, and nonregular proof entries."""
    if directory.is_symlink() or not directory.is_dir():
        raise ProofIntegrityError("proof directory is missing")
    for dirpath, dirnames, filenames in os.walk(directory, followlinks=False):
        current = Path(dirpath)
        for name in dirnames:
            path = current / name
            if path.is_symlink():
                relative = path.relative_to(directory).as_posix()
                raise ProofIntegrityError(f"proof entry is not a regular file: {relative}")
        for name in filenames:
            path = current / name
            relative = path.relative_to(directory).as_posix()
            if path.is_symlink() or not path.is_file():
                raise ProofIntegrityError(f"proof entry is not a regular file: {relative}")
            refuse_proof_payloads({relative: path.read_text(encoding="utf-8", errors="replace")})


def validate_proof_manifest(
    payload: Mapping[str, object],
    target: CapabilityProofTarget,
    expected: Mapping[str, str],
) -> ProofManifest:
    """Parse and enforce freshness, checksum, and usable-stage gates."""
    manifest = parse_proof_manifest(payload)
    refuse_missing_checksums(manifest)
    refuse_stale_fingerprints(manifest, expected)
    refuse_unvalidated_stages(manifest, target)
    return manifest
