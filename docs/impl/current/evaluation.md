# Evaluation

This page records evaluation-dataset and provided-archive proof state as it becomes available.
Fixture metrics, proof bundles, and scale pilots remain planned.

## Authorized representative archive

The operator has designated a legally usable, distribution-representative corpus slice as
`ARCHIVE_DIR`. Provided-archive proof runs and later representative-scale pilots read those
configured silos without modification, using the ordinary pipeline or stage commands. Host write
permission on the source path is acceptable and is not a readiness failure. There is no second
proof-only source root.

The designation is local configuration. Repository documentation does not record the machine path
or copy private source content. The slice is authorized for bounded processing and proof; it is
not full-corpus authorization.

Item-level gold fixtures, tuning and final split seals, and scored labels remain with
[evaluation-foundation](evaluation-foundation.md) and later
human-gated policy tasks. No final evaluation split has been opened for tuning.
Immutable local run-bundle validation and Git-bound identity export are available now; remaining
fixture and metric work is in
[create-evaluation-fixtures-and-metrics](../plan.md#create-evaluation-fixtures-and-metrics).

The slice designation is recorded in
[0023 Representative corpus approval](../records/0023-corpus-approve-representative-corpus-and-gold.md).
The path model no longer uses a second proof root; see
[0029 Retire separate proof-archive root](../records/0029-runtime-retire-separate-proof-archive-root.md).
