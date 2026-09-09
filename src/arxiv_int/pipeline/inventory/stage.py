"""Production stage adapter for content-addressed inventory."""

import hashlib
import json
import logging
from dataclasses import asdict
from pathlib import Path

from arxiv_int.interfaces.pipeline import StageContext, StageResult
from arxiv_int.interfaces.stores import DatasetRef, ValidationResultRef
from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.inventory.checkpoint import Checkpoint
from arxiv_int.pipeline.inventory.model import DEFAULT_POLICY, InventoryPolicy
from arxiv_int.pipeline.inventory.publish import atomic_json, publish, validate_manifest
from arxiv_int.pipeline.inventory.snapshot import INVENTORY_METADATA_POLICY, inventory_snapshot
from arxiv_int.pipeline.run.locking import pipeline_lock
from arxiv_int.runtime.containment import overlaps, resolve_allowed_path

_LOG = logging.getLogger(__name__)


class InventoryStage:
    """One source-set stage invocation with stable occurrence-id sharding on disk."""

    stage = "inventory"
    feature = "lake"
    depends_on: tuple[str, ...] = ("preflight",)

    def __init__(self, policy: InventoryPolicy = DEFAULT_POLICY) -> None:
        self.policy = policy

    def run(self, context: StageContext) -> StageResult:
        """Resume completed files and publish only validated, immutable partitions."""
        root = inventory_root(context)
        root.mkdir(parents=True, exist_ok=True)
        if inventory_root(context) != root:
            raise ValueError("inventory output path changed")
        with pipeline_lock(root):
            return self._run(context, root)

    def _run(self, context: StageContext, root: Path) -> StageResult:
        from arxiv_int.pipeline.inventory.validate import InventoryValidator

        validator = InventoryValidator(Path(context.options["project_root"]))
        identity = json.dumps(
            {
                "generation": context.generation_id,
                "silos": [(s.silo_id, str(s.root)) for s in context.silos],
                "policy": asdict(self.policy),
                "producer": context.options.get("producer_identity", "direct"),
                "catalog": validator.fingerprint,
            },
            sort_keys=True,
        )
        checkpoint_id = hashlib.sha256(identity.encode("ascii")).hexdigest()
        scratch = Path(context.options.get("tmp_dir", str(context.results_dir / "tmp"))).resolve()
        _protect(scratch, context)
        scratch.mkdir(parents=True, exist_ok=True)
        checkpoint = Checkpoint(root / f"checkpoint-{checkpoint_id}.sqlite", identity, scratch)
        try:
            before = inventory_snapshot(context.silos)
            if context.options.get(
                "source_drift_policy"
            ) == INVENTORY_METADATA_POLICY and before != context.options.get(
                "source_metadata_snapshot"
            ):
                raise ValueError(
                    "inventory differs from the frozen source set; create an updated run"
                )
            scope = {
                silo.silo_id: checkpoint.scan(silo.root, silo.silo_id, self.policy)
                for silo in context.silos
            }
            if inventory_snapshot(context.silos) != before:
                raise ValueError("inventory source set changed during scan; create an updated run")
            manifest = publish(
                checkpoint,
                root,
                validator,
                self.policy,
                context.generation_id,
                frozenset(scope),
                scope,
            )
            summary = validate_manifest(manifest, hash_file(manifest)[0])
            summary["resumed_files"] = checkpoint.reused
            atomic_json(manifest, summary)
        finally:
            checkpoint.close()
        complete = all(scope.values())
        total = summary["rows"]
        _LOG.info(
            "inventory rows=%s silos=%s complete=%s resumed_files=%s",
            total,
            len(scope),
            complete,
            summary["resumed_files"],
        )
        output = DatasetRef(
            "source-occurrences",
            "1.0.0",
            context.generation_id,
            {
                "scan_id": context.generation_id,
                "manifest": str(manifest),
                "sha256": hash_file(manifest)[0],
            },
        )
        validation = ValidationResultRef(
            "source-occurrences", context.generation_id, validator.fingerprint, "pass", True
        )
        return StageResult(
            self.stage,
            "produced" if complete else "partial",
            f"inventory rows={total}; completed_source_set={complete}",
            (output,),
            (validation,),
        )


def inventory_root(context: StageContext) -> Path:
    """Resolve runtime output containment before any inventory writes."""
    results = context.results_dir.resolve()
    _protect(results, context)
    target = (
        results
        / "normalized/inventory/contract_version=1.0.0"
        / (f"scan_id={context.generation_id}")
    )
    resolved = resolve_allowed_path(target, (results,))
    if resolved != target:
        raise ValueError("inventory output path must not traverse symlinks")
    return resolved


def _protect(candidate: Path, context: StageContext) -> None:
    roots = [
        Path(context.options["project_root"]).resolve(),
        *(silo.root.resolve() for silo in context.silos),
        *(
            Path(value).resolve()
            for value in json.loads(context.options.get("protected_roots", "[]"))
        ),
    ]
    if candidate == Path(candidate.anchor) or any(overlaps(candidate, root) for root in roots):
        raise ValueError("inventory output overlaps protected roots")
