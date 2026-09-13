"""Validate ordinary classification attempts and their complete upstream chain."""

from pathlib import Path
from typing import Any

from arxiv_int.classification.artifacts import (
    CLASSIFICATION_CLASSES,
    FILE_CLASSIFICATIONS,
    validate_manifest,
)
from arxiv_int.classification.layout import ClassificationLayout
from arxiv_int.classification.policy import load_classifier_policy
from arxiv_int.classification.vocabulary.policy import load_scheme_policy
from arxiv_int.classification.vocabulary.snapshot import check_snapshot, load_snapshot
from arxiv_int.pipeline.control.artifacts import hash_file, validate_attempt
from arxiv_int.pipeline.control.fingerprints import reuse_key
from arxiv_int.pipeline.dag.execute import stage_identity
from arxiv_int.pipeline.dag.stages import production_registry
from arxiv_int.pipeline.quality.evidence import validate_quality_evidence
from arxiv_int.pipeline.reconcile.scan import bind_shard
from arxiv_int.pipeline.run.context import RunContext
from arxiv_int.pipeline.run.persist import RunStatus, load_json
from tests.integration.corpus.artifacts import require, validate_contracts, validate_execution

STAGES = ("preflight", "inventory", "extract", "normalize", "classify")


def validate_classification_run(
    context: RunContext, status: RunStatus
) -> tuple[dict[str, Any], dict[str, tuple[Path, dict[str, Any]]]]:
    """Rehash sealed attempts, contract batches, scheme and exact upstream references."""
    require(not status.halted, "classification closure halted")
    selected = {item.stage: item for item in status.executions}
    require(len(selected) == len(status.executions), "duplicate stage execution")
    require(set(selected) == set(STAGES), "classification closure is incomplete")
    registry = production_registry()
    producers: dict[str, Any] = {}
    for item in selected.values():
        require(
            item.status in {"succeeded", "quarantined"}, "classification closure has a failed stage"
        )
        validate_attempt(Path(item.directory or ""), reuse_key=item.reuse_key, attempt=item.attempt)
        spec = registry.get(item.stage)
        identity = stage_identity(
            spec,
            bind_shard(context, item.shard_id),
            tuple(selected[name].reuse_key for name in spec.depends_on),
        )
        require(reuse_key(identity) == item.reuse_key, "stage producer fingerprints are stale")
        manifest = Path(item.directory or "") / "manifest.json"
        producers[item.stage] = {
            "owned": dict(identity.owned),
            "reuseKey": item.reuse_key,
            "manifest": str(manifest),
            "sha256": hash_file(manifest)[0],
        }
    snapshots = {
        name: validate_execution(selected[name], context.project_root)
        for name in ("inventory", "extract", "normalize")
    }
    directory = Path(selected["classify"].directory or "")
    output = load_json(directory / "stage.json")["outputs"][0]
    require(
        validate_quality_evidence(directory, output["generationId"]),
        "classification quality evidence is invalid",
    )
    pointer = output["partition"]
    manifest = Path(pointer["manifest"])
    summary = validate_manifest(manifest, pointer["sha256"])
    validate_contracts(
        summary, (FILE_CLASSIFICATIONS, CLASSIFICATION_CLASSES), context.project_root
    )
    for upstream, stage in (
        ("inventory", "inventory"),
        ("extraction", "extract"),
        ("normalization", "normalize"),
    ):
        expected = load_json(Path(selected[stage].directory or "") / "stage.json")
        partition = expected["outputs"][0]["partition"]
        require(
            summary["upstream"][upstream]
            == {key: partition[key] for key in ("manifest", "sha256")},
            "classification upstream reference does not match executed closure",
        )
        if stage == "inventory":
            require(
                partition["scan_id"] == expected["outputs"][0]["generationId"],
                "inventory scan id drift",
            )
    layout = ClassificationLayout.for_run(context.runs_dir, context.run_id)
    require(
        not check_snapshot(layout.scheme, load_scheme_policy(context.project_root)),
        "classification scheme is stale or damaged",
    )
    scheme = load_snapshot(layout.scheme)
    require(
        summary["scheme"]["content_sha256"] == scheme.manifest["contentSha256"],
        "mapping uses a different scheme snapshot",
    )
    policy = load_classifier_policy(context.project_root)
    require(
        summary["classifier"]["classifier_id"] == policy.classifier_id
        and summary["classifier"]["configuration_sha256"] == policy.sha256,
        "mapping classifier identity is stale",
    )
    packet = load_json(layout.review / "operating-point.json")
    require(
        packet["mappingManifest"] == {"path": str(manifest), "sha256": pointer["sha256"]},
        "review packet names another mapping",
    )
    for packet_key, summary_key in (
        ("accounting", "accounting"),
        ("upstream", "upstream"),
        ("classifier", "classifier"),
        ("scheme", "scheme"),
        ("countsByPrimary", "counts_by_primary"),
        ("runtime", "runtime"),
    ):
        require(packet[packet_key] == summary[summary_key], "review packet identity/count drift")
    summary["checked_manifest"] = pointer
    summary["checked_producers"] = producers
    return summary, snapshots
