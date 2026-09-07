"""Require current model and test evidence before publishing derived relations."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from arxiv_int.transformations.artifacts import load_json
from arxiv_int.transformations.credentials import sanitize_generation_id


class ValidationEvidenceError(ValueError):
    """Required model, relation or data-test evidence is missing or invalid."""


def validated_relations(artifact_dir: Path, generation: str, command: str) -> tuple[str, ...]:
    """Resolve selected model relations only after every attached test passed."""
    manifest = load_json(artifact_dir / "manifests" / "manifest.json")
    results = load_json(artifact_dir / "manifests" / "run_results.json")
    invocation = manifest.get("metadata", {}).get("invocation_id")
    if not invocation or results.get("metadata", {}).get("invocation_id") != invocation:
        raise ValidationEvidenceError("missing current dbt invocation evidence")
    nodes = manifest.get("nodes", {})
    outcomes = {item["unique_id"]: item for item in results.get("results", [])}
    if not outcomes or any(
        item.get("status") not in {"success", "pass"} for item in outcomes.values()
    ):
        raise ValidationEvidenceError("missing or unsuccessful dbt model/test outcomes")
    models = _selected_models(nodes, outcomes, command)
    required = {
        key
        for key, node in nodes.items()
        if node.get("resource_type") == "test"
        and models.intersection(node.get("depends_on", {}).get("nodes", []))
    }
    if not models or not required or not required.issubset(outcomes):
        raise ValidationEvidenceError("selected models have missing required data tests")
    if any(outcomes[key].get("status") != "pass" for key in required):
        raise ValidationEvidenceError("required data tests did not pass")
    return tuple(sorted(_relation(nodes[key], generation) for key in models))


def _selected_models(
    nodes: Mapping[str, Any], outcomes: Mapping[str, Any], command: str
) -> set[str]:
    if command == "build":
        return {key for key in outcomes if nodes.get(key, {}).get("resource_type") == "model"}
    dependencies = {
        dep for key in outcomes for dep in nodes.get(key, {}).get("depends_on", {}).get("nodes", [])
    }
    return {key for key in dependencies if nodes.get(key, {}).get("resource_type") == "model"}


def _relation(node: Mapping[str, Any], generation: str) -> str:
    alias = str(node.get("alias") or "")
    name = str(node.get("name") or "")
    if (
        node.get("schema") != "derived"
        or sanitize_generation_id(name) != name
        or alias != f"{name}__g_{generation}"
    ):
        raise ValidationEvidenceError("selected model is outside its isolated derived generation")
    return f"derived.{alias}"
