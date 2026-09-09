# Evaluation

This page records evaluation-dataset and provided-archive proof state as it becomes available.
Frozen synthetic fixtures, paired metrics, the `evaluate` stage, and a proof dispatcher exist.
The pipeline-control provided-archive proof is published; remaining provided-archive proofs and
scale pilots stay planned.

## Authorized representative archive

The operator has designated a legally usable, distribution-representative corpus slice as
`ARCHIVE_DIR`. Provided-archive proof runs and later representative-scale pilots read those
configured silos without modification, using the ordinary pipeline or stage commands. Host write
permission on the source path is acceptable and is not a readiness failure. There is no second
proof-only source root.

The designation is local configuration. Repository documentation does not record the machine path
or copy private source content. The slice is authorized for bounded processing and proof; it is
not full-corpus authorization.

Item-level gold fixtures, tuning and final split seals, and scored labels are documented in
[evaluation-foundation](evaluation-foundation.md). Human-gated policy tasks still own review of
real-archive gold. No final evaluation split has been opened for tuning on the provided archive.
Immutable local run-bundle validation, Git-bound identity export, frozen synthetic fixtures,
paired metrics, the `evaluate` stage, and `make proof` are available now. See
[record 0036](../records/0036-eval-found-create-evaluation-fixtures-and-metrics.md)
and the inference/evaluation checkpoint
[record 0038](../records/0038-eval-found-review-inference-and-evaluation-boundaries.md).

The slice designation is recorded in
[0023 Representative corpus approval](../records/0023-corpus-approve-representative-corpus-and-gold.md).
The path model no longer uses a second proof root; see
[0029 Retire separate proof-archive root](../records/0029-runtime-retire-separate-proof-archive-root.md).
The pipeline-control proof is recorded in
[0053 Pipeline-control provided-archive proof](../records/0053-pipeline-prove-pipeline-control-on-provided-archive.md).
