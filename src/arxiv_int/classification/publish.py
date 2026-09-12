"""Publish file mappings and their frozen scheme as one validated immutable snapshot."""

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from arxiv_int.classification.artifacts import (
    CLASSIFICATION_CLASSES,
    DATASETS,
    FILE_CLASSIFICATIONS,
    LAYOUT,
    SCHEMA,
)
from arxiv_int.classification.model import Classification, ClassifierPolicy, PhysicalFile
from arxiv_int.classification.model import classification_id as build_classification_id
from arxiv_int.pipeline.lake.publish import SnapshotPublisher
from arxiv_int.pipeline.lake.validate import SnapshotValidator


class ClassificationPublisher:
    """Bound and publish complete classifications in configured-size batches."""

    def __init__(
        self,
        results: Path,
        generation: str,
        validator: SnapshotValidator,
        policy: ClassifierPolicy,
        scheme_id: str,
        run_id: str,
        extraction_fingerprint: str,
        normalizer_id: str,
    ) -> None:
        self.snapshot = SnapshotPublisher(
            results, "classify", generation, validator, LAYOUT, DATASETS, policy.batch_rows
        )
        self.generation = generation
        self.policy = policy
        self.scheme_id = scheme_id
        self.run_id = run_id
        self.extraction_fingerprint = extraction_fingerprint
        self.normalizer_id = normalizer_id
        self.counts: Counter[str] = Counter()
        self.rows = 0

    def add_scheme(self, rows: Sequence[Mapping[str, Any]]) -> None:
        """Publish the exact scheme rows consumed by this classifier generation."""
        for source in rows:
            row = dict(source)
            row["generation_id"] = self.generation
            metadata = {"scheme_class_id": row["scheme_class_id"]}
            self.snapshot.add_row(CLASSIFICATION_CLASSES, row, metadata)

    def add(self, item: PhysicalFile, classification: Classification) -> None:
        """Publish one canonical physical-file mapping with complete evidence."""
        identity = build_classification_id(
            item.occurrence_id, self.scheme_id, self.policy.classifier_id
        )
        candidates = [
            {
                "class_id": candidate.class_id,
                "score": round(candidate.score, 12),
                "matched_terms": list(candidate.matched_terms),
            }
            for candidate in classification.candidates
        ]
        row: dict[str, object] = {
            "classification_id": identity,
            "occurrence_id": item.occurrence_id,
            "document_id": classification.document_ids[0] if classification.document_ids else None,
            "silo_id": item.silo_id,
            "relative_path": item.relative_path,
            "primary_class_id": classification.primary,
            "alternate_class_ids_json": json.dumps(
                list(classification.alternates), ensure_ascii=True
            ),
            "ancestor_path": ">".join(classification.path),
            "confidence": classification.confidence,
            "calibration_profile": self.policy.profile_id,
            "scores_json": json.dumps(candidates, ensure_ascii=True, sort_keys=True),
            "evidence_json": json.dumps(classification.evidence, ensure_ascii=True, sort_keys=True),
            "failure_reason": classification.failure_reason,
            "extraction_fingerprint": self.extraction_fingerprint,
            "normalizer_id": self.normalizer_id,
            "classifier_id": self.policy.classifier_id,
            "configuration_sha256": self.policy.sha256,
            "scheme_id": self.scheme_id,
            "review_state": "proposed",
            "run_id": self.run_id,
            "generation_id": self.generation,
            "contract_version": "1.0.0",
            "bucket": identity[0],
        }
        metadata: dict[str, object] = {
            "classification_id": identity,
            "content_hash": item.content_hash,
            "document_ids": list(classification.document_ids),
        }
        self.snapshot.add_row(FILE_CLASSIFICATIONS, row, metadata)
        self.rows += 1
        self.counts[classification.primary] += 1

    def finish(
        self,
        *,
        upstream: Mapping[str, Mapping[str, str]],
        scheme: Mapping[str, object],
        scheme_rows: int,
        elapsed_seconds: float,
        peak_memory_mib: float,
        physical_inventory_rows: int,
        virtual_member_rows: int,
    ) -> Path:
        """Seal a complete mapping and its content-free runtime evidence."""
        if self.rows != physical_inventory_rows:
            raise ValueError(
                f"classification accounting mismatch: {self.rows} rows for "
                f"{physical_inventory_rows} physical inventory files"
            )
        throughput = self.rows / max(elapsed_seconds, 1e-9)
        return self.snapshot.finish(
            SCHEMA,
            {"file_classifications": self.rows, "classification_classes": scheme_rows},
            {
                "accounting": {
                    "physical_inventory_rows": physical_inventory_rows,
                    "virtual_member_rows": virtual_member_rows,
                    "classified_rows": self.rows,
                },
                "classifier": {
                    "algorithm_version": self.policy.algorithm_version,
                    "classifier_id": self.policy.classifier_id,
                    "configuration_sha256": self.policy.sha256,
                    "profile_id": self.policy.profile_id,
                    "profile_version": self.policy.profile_version,
                    "thresholds": {
                        "alternate": self.policy.alternate_threshold,
                        "margin": self.policy.margin_threshold,
                        "primary": self.policy.primary_threshold,
                    },
                },
                "counts_by_primary": dict(sorted(self.counts.items())),
                "runtime": {
                    "elapsed_seconds": elapsed_seconds,
                    "peak_memory_mib": peak_memory_mib,
                    "throughput_files_per_second": throughput,
                },
                "reproducibility": {"checked_rows": self.rows, "status": "pass"},
                "scheme": dict(scheme),
                "upstream": {name: dict(value) for name, value in sorted(upstream.items())},
            },
        )

    def abort(self) -> None:
        """Remove an unpublished classification snapshot."""
        self.snapshot.abort()
