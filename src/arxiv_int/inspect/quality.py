"""Read retained quality.json, published Pandera evidence, and sanitized dbt lineage."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from arxiv_int.inspect.model import (
    CONFORMANCE_DRIFTED,
    CONFORMANCE_MATCHING,
    CONFORMANCE_UNREGISTERED,
    LineageSummary,
    QualityRuleSummary,
)
from arxiv_int.pipeline.run.persist import load_json

QUALITY_KEYS = frozenset({"generation_id", "checks", "validations", "transformations"})
STAGE_KEYS = frozenset({"detail", "outcome", "outputs", "stage"})
MANIFEST_KEYS = frozenset({"attempt", "files", "reuseKey"})


def contract_versions(project_root: Path) -> dict[str, str]:
    """Load current ODCS versions; missing contracts yield an empty map."""
    try:
        from arxiv_int.contracts.catalog.registry import FileRegistry
        from arxiv_int.contracts.lint import contracts_root_for

        registry = FileRegistry(contracts_root_for(project_root))
    except (OSError, ValueError, TypeError):
        return {}
    versions: dict[str, str] = {}
    for contract_id in registry.contract_ids():
        try:
            odcs = registry.load_odcs(contract_id)
        except (OSError, ValueError, TypeError, KeyError):
            versions[contract_id] = ""
            continue
        versions[contract_id] = str(odcs.get("version") or "")
    return versions


def conformance(dataset: str, version: str, versions: Mapping[str, str]) -> str:
    """Compare one artifact contract identity to the current registry."""
    if dataset not in versions:
        return CONFORMANCE_UNREGISTERED
    current = versions[dataset]
    if current and version == current:
        return CONFORMANCE_MATCHING
    return CONFORMANCE_DRIFTED


def payload_drifted(payload: Mapping[str, Any], required: frozenset[str]) -> bool:
    """Report whether a retained JSON object is missing required keys."""
    return not required.issubset(payload)


def load_quality(
    directory: Path,
) -> tuple[tuple[QualityRuleSummary, ...], tuple[LineageSummary, ...], bool]:
    """Read ``quality.json`` without invoking Pandera or dbt."""
    path = directory / "quality.json"
    if not path.is_file():
        return (), (), True
    try:
        payload = load_json(path)
    except (OSError, ValueError):
        return (), (), True
    drifted = payload_drifted(payload, QUALITY_KEYS) or not isinstance(payload.get("checks"), list)
    checks = tuple(_check(item) for item in _objects(payload.get("checks")))
    lineage = tuple(_lineage(item) for item in _objects(payload.get("transformations")))
    return checks, lineage, drifted


def published_quality(runs_dir: Path, run_id: str, *, limit: int) -> tuple[QualityRuleSummary, ...]:
    """Read ``$RUNS_DIR/<run-id>/quality/result.json`` when present."""
    path = runs_dir / run_id / "quality" / "result.json"
    if not path.is_file():
        return ()
    try:
        payload = load_json(path)
    except (OSError, ValueError):
        return ()
    checks = [_check(item) for item in _objects(payload.get("checks"))]
    return tuple(checks[:limit])


def published_lineage(runs_dir: Path, run_id: str, *, limit: int) -> tuple[LineageSummary, ...]:
    """Read sanitized dbt run-results or model ids from published manifests."""
    results_path = runs_dir / run_id / "manifests" / "run_results.json"
    parsed = _run_results(results_path, limit) if results_path.is_file() else ()
    if parsed:
        return parsed
    return _manifest_models(runs_dir / run_id / "manifests" / "manifest.json", limit)


def _manifest_models(path: Path, limit: int) -> tuple[LineageSummary, ...]:
    if not path.is_file():
        return ()
    try:
        payload = load_json(path)
    except (OSError, ValueError):
        return ()
    if "reuseKey" in payload or "files" in payload:
        return ()
    return _model_nodes(payload.get("nodes"), limit)


def _model_nodes(nodes: object, limit: int) -> tuple[LineageSummary, ...]:
    if not isinstance(nodes, dict):
        return ()
    rows: list[LineageSummary] = []
    for unique_id, node in sorted(nodes.items()):
        row = _model_node(str(unique_id), node)
        if row is None:
            continue
        rows.append(row)
        if len(rows) >= limit:
            break
    return tuple(rows)


def _model_node(unique_id: str, node: object) -> LineageSummary | None:
    if not isinstance(node, dict):
        return None
    resource = str(node.get("resource_type") or node.get("resourceType") or "model")
    if resource != "model":
        return None
    raw = node.get("checksum")
    digest = unique_id[:64]
    if isinstance(raw, dict):
        digest = str(raw.get("checksum") or unique_id)[:64]
    return LineageSummary("build", "retained", digest, digest, False)


def _run_results(path: Path, limit: int) -> tuple[LineageSummary, ...]:
    try:
        payload = load_json(path)
    except (OSError, ValueError):
        return ()
    rows: list[LineageSummary] = []
    for item in _objects(payload.get("results")):
        unique_id = str(item.get("unique_id") or item.get("uniqueId") or "")
        if not unique_id:
            continue
        status = str(item.get("status") or "unknown")
        rows.append(LineageSummary("build", status, unique_id, unique_id, status == "success"))
        if len(rows) >= limit:
            break
    return tuple(rows)


def _check(item: Mapping[str, Any]) -> QualityRuleSummary:
    status = str(_get(item, "status") or "not-run")
    failed = _get(item, "failed_count", "failedCount")
    required = _get(item, "required")
    return QualityRuleSummary(
        str(_get(item, "rule_id", "ruleId") or "unknown"),
        str(_get(item, "scope") or "unknown"),
        status,
        _optional_count(failed),
        True if required is None else bool(required),
    )


def _lineage(item: Mapping[str, Any]) -> LineageSummary:
    return LineageSummary(
        str(_get(item, "command") or "build"),
        str(_get(item, "status") or "unknown"),
        str(_get(item, "input_fingerprint", "inputFingerprint") or "missing"),
        str(_get(item, "model_fingerprint", "modelFingerprint") or "missing"),
        bool(_get(item, "activatable") or False),
    )


def _objects(value: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, dict))


def _optional_count(value: object) -> int:
    if value is None or value == "":
        return 0
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def _get(item: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in item:
            return item[name]
    return None
