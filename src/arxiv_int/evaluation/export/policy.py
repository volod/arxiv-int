"""Versioned SHA-256 namespace and committed proof-identity policy document."""

from collections.abc import Mapping
from pathlib import Path

from arxiv_int.evaluation.bundles.layout import digest_bytes
from arxiv_int.evaluation.bundles.manifest import canonical_json
from arxiv_int.resources.paths import configs_output_root, configs_root

POLICY_ID = "arxiv-int.proof-identity.v1"
POLICY_VERSION = 1
NAMESPACE = "arxiv-int/proof-identity/v1"
DATA_CLASS_TRANSFORMED = "transformed"
POLICY_FILENAME = "proof-identity-policy.json"
IDENTITIES_ARTIFACT = "identities.json"
RESERVED_EXPORT_ARTIFACTS = frozenset({IDENTITIES_ARTIFACT})
ENTITY_KINDS = ("person", "company", "product")
FIELD_KINDS = ("email", "phone", "address", "account")
ACCOUNT_SCHEMES = ("digits", "luhn", "iban", "inn10", "inn12")
EMAIL_DOMAIN = "example.invalid"
TEXT_EXTENSIONS = frozenset(
    {".csv", ".html", ".json", ".jsonl", ".md", ".svg", ".tsv", ".txt", ".yaml", ".yml"}
)
JSON_EXTENSIONS = frozenset({".json"})
JSONL_EXTENSIONS = frozenset({".jsonl"})
UNSUPPORTED_EXTENSIONS = frozenset(
    {
        ".bin",
        ".bmp",
        ".gif",
        ".gz",
        ".ico",
        ".jpeg",
        ".jpg",
        ".mp3",
        ".mp4",
        ".pdf",
        ".png",
        ".sqlite",
        ".tif",
        ".tiff",
        ".webp",
        ".zip",
    }
)
TRANSFORM_MARK = {
    "data_class": DATA_CLASS_TRANSFORMED,
    "policy_id": POLICY_ID,
    "policy_version": POLICY_VERSION,
}


def policy_document() -> dict[str, object]:
    """Return the version-1 public policy object."""
    return {
        "account_schemes": list(ACCOUNT_SCHEMES),
        "data_class": DATA_CLASS_TRANSFORMED,
        "email_domain": EMAIL_DOMAIN,
        "entity_kinds": list(ENTITY_KINDS),
        "field_kinds": list(FIELD_KINDS),
        "identities_artifact": IDENTITIES_ARTIFACT,
        "namespace": NAMESPACE,
        "policy_id": POLICY_ID,
        "policy_version": POLICY_VERSION,
        "raw_maps_local_only": True,
        "strong_cryptography": False,
    }


def policy_bytes() -> bytes:
    """Return the canonical committed policy document."""
    return canonical_json(policy_document())


def policy_fingerprint(document: Mapping[str, object] | None = None) -> str:
    """Return the SHA-256 fingerprint of the canonical policy bytes."""
    payload = canonical_json(dict(document) if document is not None else policy_document())
    return digest_bytes(payload)


def policy_root(project_root: Path) -> Path:
    """Return the committed evaluation-policy directory."""
    return configs_root(project_root) / "evaluation"


def generate_policy(project_root: Path) -> Path:
    """Write the committed policy document and return its path."""
    root = configs_output_root(project_root) / "evaluation"
    root.mkdir(parents=True, exist_ok=True)
    path = root / POLICY_FILENAME
    path.write_bytes(policy_bytes())
    return path


def check_policy_drift(project_root: Path) -> tuple[str, ...]:
    """Return drift findings; an empty tuple means the committed policy matches."""
    path = policy_root(project_root) / POLICY_FILENAME
    expected = policy_bytes()
    if not path.is_file():
        return ("proof-identity policy file is missing",)
    actual = path.read_bytes()
    if actual != expected:
        return (f"generated policy drifted: {POLICY_FILENAME}",)
    return ()


def namespaced_digest(kind: str, normalized: str) -> str:
    """Return SHA-256(namespace, kind, normalized) as lowercase hex."""
    material = "\x00".join((NAMESPACE, kind, normalized)).encode("utf-8")
    return digest_bytes(material)
