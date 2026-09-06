# Design

The [product specification](spec.md) is the living source of truth for product behavior. It includes
the capability registry, the evaluation contract for each capability, explicit boundaries, and the
process for adding capabilities discovered during implementation.

The registry order is the implementation line followed by the
[forward plan](../impl/plan.md). `make lint-spec-plan` makes disagreement between those documents a
build failure.

Current behavior is indexed by [current implementation](../impl/current.md).

The [execution architecture](architecture.md) describes the runtime DAG, module ownership,
generation publication, and first complete archive-to-report slice.
