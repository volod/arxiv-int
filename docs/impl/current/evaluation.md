# Evaluation

This page records evaluation datasets and provided-archive integration state.

## Authorized representative archive

The operator has designated a legally usable, distribution-representative corpus slice as
`ARCHIVE_DIR`. Archive integration and later representative-scale pilots read configured silos
without modification through the ordinary pipeline. Host write permission on the source path is
acceptable and is not a readiness failure. There is no second test-only source root.

The designation is local configuration. Repository documentation does not record the machine path
or copy private source content. The slice is authorized for bounded processing and integration
checks; it is not full-corpus authorization. Human-gated policy tasks still own review of real
archive gold, and no final evaluation split has been opened for tuning on this archive.

Reusable metrics and result bundles are documented in
[evaluation foundation](evaluation-foundation.md). The corpus archive integration test is documented
there and in [corpus foundation](corpus-foundation.md#provided-archive-integration). Earlier
pipeline-control and corpus proof bundles remain historical evidence in accepted records; their
special-purpose production publishers and disposable experiment were removed by
[record 0069](../records/0069-govern-retire-milestone-evaluation-scaffolding.md).

The slice designation is recorded in
[0023 Representative corpus approval](../records/0023-corpus-approve-representative-corpus-and-gold.md).
The path model no longer uses a second proof root; see
[0029 Retire separate proof-archive root](../records/0029-runtime-retire-separate-proof-archive-root.md).
