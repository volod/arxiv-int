"""Write, load, and re-verify immutable scheme snapshot directories.

A snapshot is ``classes.jsonl`` plus ``report.json`` and, written last, ``manifest.json`` with
file checksums. Checking recomputes checksums, content identity, derived closure and tokens, and
compares the policy, taxonomy, source, extension and builder fingerprints with the current
configuration, so a tampered or out-of-date snapshot is reported as stale instead of reused.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from arxiv_int.classification.layout import write_jsonl
from arxiv_int.classification.vocabulary.build import (
    BUILDER_VERSION,
    BuiltScheme,
    content_sha256,
    scheme_class_id,
)
from arxiv_int.classification.vocabulary.model import (
    ANCESTOR_SEPARATOR,
    Scheme,
    SchemeClass,
    caption_pairs,
)
from arxiv_int.classification.vocabulary.policy import Licence, SchemePolicy
from arxiv_int.classification.vocabulary.tokens import class_token
from arxiv_int.classification.vocabulary.validate import (
    Finding,
    validate_classes,
    validate_licence,
)
from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.run.persist import write_json

CLASSES_FILE = "classes.jsonl"
MANIFEST_FILE = "manifest.json"
REPORT_FILE = "report.json"


class SnapshotError(RuntimeError):
    """Raised when a snapshot cannot be written or read."""


@dataclass(frozen=True)
class Snapshot:
    """A loaded snapshot: manifest, rows, and the rebuilt scheme."""

    manifest: dict[str, Any]
    rows: tuple[dict[str, Any], ...]
    scheme: Scheme


def report_payload(built: BuiltScheme) -> dict[str, Any]:
    """Return the finding report written beside every build attempt."""
    return {
        "findings": [
            {
                "classId": item.class_id,
                "code": item.code,
                "message": item.message,
                "severity": item.severity,
            }
            for item in built.findings
        ],
        "publishable": built.publishable,
        "schemeId": built.scheme_id or None,
    }


def write_snapshot(directory: Path, built: BuiltScheme) -> Path:
    """Write a new snapshot directory; refuse to overwrite an existing one."""
    if directory.exists() and any(directory.iterdir()):
        raise SnapshotError(f"refusing to overwrite existing snapshot {directory.name}")
    directory.mkdir(parents=True, exist_ok=True)
    write_json(directory / REPORT_FILE, report_payload(built))
    if not built.publishable:
        return directory / REPORT_FILE
    write_jsonl(directory / CLASSES_FILE, built.rows)
    files = {}
    for name in (CLASSES_FILE, REPORT_FILE):
        digest, size = hash_file(directory / name)
        files[name] = {"bytes": size, "sha256": digest}
    write_json(directory / MANIFEST_FILE, {**built.manifest, "files": files})
    return directory / MANIFEST_FILE


def rows_to_classes(rows: Sequence[dict[str, Any]]) -> list[SchemeClass]:
    """Rebuild scheme classes from frozen rows."""
    return [
        SchemeClass(
            class_id=str(row["class_id"]),
            namespace=str(row["namespace"]),
            code=row.get("code"),
            parent_id=row.get("parent_class_id"),
            kind=str(row["class_kind"]),
            captions=caption_pairs(json.loads(str(row["captions_json"]))),
            crosswalk=tuple(json.loads(str(row.get("crosswalk_json") or "[]"))),
        )
        for row in rows
    ]


def load_snapshot(directory: Path) -> Snapshot:
    """Load a published snapshot without verifying it (see :func:`check_snapshot`)."""
    manifest_path = directory / MANIFEST_FILE
    if not (directory / REPORT_FILE).is_file():
        raise SnapshotError(
            "no scheme snapshot found; build one with "
            "`arxiv-int classification build-scheme --run-id RUN_ID`"
        )
    if not manifest_path.is_file():
        raise SnapshotError(f"the last build did not publish; see {REPORT_FILE} for its findings")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    with (directory / CLASSES_FILE).open(encoding="ascii") as handle:
        rows = tuple(json.loads(line) for line in handle if line.strip())
    return Snapshot(manifest, rows, Scheme.of(rows_to_classes(rows)))


def _stale(message: str) -> Finding:
    return Finding("stale-snapshot", "error", None, message)


def _file_findings(directory: Path, manifest: dict[str, Any]) -> list[Finding]:
    return [
        _stale(f"{name} checksum differs from the manifest")
        for name, record in sorted((manifest.get("files") or {}).items())
        if not (directory / name).is_file()
        or hash_file(directory / name)[0] != record.get("sha256")
    ]


def _identity_findings(snapshot: Snapshot, policy: SchemePolicy) -> list[Finding]:
    manifest = snapshot.manifest
    sources = tuple(item.get("sha256") for item in manifest.get("sources") or ())
    expected = {
        "builder": (manifest.get("builderVersion"), BUILDER_VERSION),
        "policy": ((manifest.get("policy") or {}).get("sha256"), policy.policy_sha256),
        "taxonomy": ((manifest.get("taxonomy") or {}).get("sha256"), policy.taxonomy.sha256),
        "sources": (sources, policy.sources_sha256),
        "extensions": ((manifest.get("extensions") or {}).get("sha256"), policy.extensions_sha256),
        "content": (manifest.get("contentSha256"), content_sha256(snapshot.rows)),
    }
    found = [
        _stale(f"{label} fingerprint differs from the current configuration")
        for label, (recorded, current) in expected.items()
        if recorded != current
    ]
    scheme_id = str(manifest.get("schemeId"))
    if {row.get("scheme_id") for row in snapshot.rows} != {scheme_id} or any(
        row.get("scheme_class_id") != scheme_class_id(scheme_id, str(row["class_id"]))
        for row in snapshot.rows
    ):
        found.append(_stale("row scheme ids differ from the manifest"))
    return found


def _derived_findings(snapshot: Snapshot) -> list[Finding]:
    found: list[Finding] = []
    for row in snapshot.rows:
        class_id = str(row["class_id"])
        try:
            ancestors = ANCESTOR_SEPARATOR.join(snapshot.scheme.ancestors(class_id))
        except (KeyError, ValueError) as problem:
            found.append(Finding("orphan-parent", "error", class_id, str(problem)))
            continue
        if row["ancestor_path"] != ancestors or row["depth"] != snapshot.scheme.depth(class_id):
            found.append(_stale(f"{class_id} parent closure differs from its parent links"))
        if row["path_token"] != class_token(class_id):
            found.append(_stale(f"{class_id} path token differs from the token rule"))
    return found


def _manifest_licence(manifest: dict[str, Any]) -> Licence:
    licence = (manifest.get("taxonomy") or {}).get("licence") or {}
    return Licence(str(licence.get("name") or ""), str(licence.get("url") or ""))


def check_snapshot(
    directory: Path, policy: SchemePolicy, *, expect_scheme_id: str | None = None
) -> list[Finding]:
    """Return every finding for a published snapshot; empty means current and intact."""
    try:
        snapshot = load_snapshot(directory)
    except (OSError, ValueError, SnapshotError) as problem:
        return [_stale(str(problem))]
    found = _file_findings(directory, snapshot.manifest)
    found.extend(_identity_findings(snapshot, policy))
    if expect_scheme_id is not None and snapshot.manifest.get("schemeId") != expect_scheme_id:
        found.append(_stale(f"expected scheme {expect_scheme_id}"))
    found.extend(validate_classes(rows_to_classes(snapshot.rows), policy))
    found.extend(validate_licence("taxonomy", _manifest_licence(snapshot.manifest)))
    if not found:
        found.extend(_derived_findings(snapshot))
    return found
