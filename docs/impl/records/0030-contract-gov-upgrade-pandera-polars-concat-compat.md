# Task Record

## Task and scope

- Id / capability / checkpoint: `upgrade-pandera-polars-concat-compat` / `contract-governance` /
  `review-corpus-and-control-integrity`
- State: accepted
- Source: ad hoc request to remove the `make ci` DeprecationWarning from
  `tests/stores/test_canonical_schema_units.py::test_validate_rows_rejects_null_document_id`.
- Initial count: 76 tasks (66 agent, 10 human); next agent task remains
  `implement-local-inference-adapters`.
- Accepted task:

```markdown
#### upgrade-pandera-polars-concat-compat

Keep contract batch validation warning-free on current Polars by pinning Pandera to the release
that no longer uses deprecated horizontal concat.

- Serves: `contract-governance` --
[Data transformations and quality](../design/spec.md#data-transformations-and-quality)
- Agent status: CLEAR
- Task kind: refactor
- Dependencies: [Contract data-quality checks](records/0019-contract-gov-implement-contract-data-quality-checks.md).
- User-visible outcome: Rejecting a null required identifier during staging quality does not emit a
Polars concat DeprecationWarning from `make ci`.
- Scope boundary: Bump the pinned `data-quality` Pandera extra to the upstream concat fix and keep
the lake Polars floor compatible with that extra. Do not change contract rules, staging SQL, or
pytest warning filters.
- Data and artifact paths: `pyproject.toml`, `uv.lock`,
`tests/stores/test_canonical_schema_units.py`, and [Contracts](../current/contracts.md).
- Execution path: Pin `pandera[polars]==0.33.1`, raise the Polars extra floor to 1.20, refresh the
lock, and assert the null-document-id rejection path emits no concat deprecation.
- Acceptance gates: The named unit test passes without the Polars concat DeprecationWarning;
`make ci` stays warning-clean for that path.
- Documentation target: `docs/impl/current/contracts.md`
- Review checkpoint: `review-corpus-and-control-integrity`.
```

- Amendments: none.

## Implementation

Pandera 0.28.0 called `pl.concat(..., how="horizontal")` while collecting not-nullable failures.
Polars 1.42.1 deprecates that default, so the staging null-document-id path warned during `make ci`.
The extra is now `pandera[polars]==0.33.1`, which concatenates with `how="horizontal_extend"` on
current Polars. The lake extra floor is `polars>=1.20,<2` to match Pandera's polars extra. The
named unit test asserts the rejection path emits no concat deprecation. Current state:
[contracts](../current/contracts.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Null required identifier rejected without concat deprecation | `.venv/bin/python -m pytest tests/stores/test_canonical_schema_units.py::test_validate_rows_rejects_null_document_id tests/data_quality -W error::DeprecationWarning` | pass; 60 tests; DeprecationWarning is an error |
| `make lint-spec-plan` | `make lint-spec-plan` | pass; 0 findings; 76 tasks (66 agent, 10 human) |
| `make lint-doc-links` | `make lint-doc-links` | pass; 0 broken links |
| `make ci` | `make ci` | pass; 791 passed, 18 skipped; no pytest warnings |
| `make quality` | `make quality` | pass; 791 passed, 18 skipped; coverage 90%; wheels built |

## Audit handoff

none identified. Reviewed that the pin bump stays inside the data-quality extra, that Polars
1.20 is the floor Pandera 0.33 requires, and that no pytest warning filter was added.

## Close or resume

Accepted. Plan counts: 76 tasks before and after (ad hoc pin; not added to remaining work).
Capability `contract-governance` remains shipped. Next agent work is unchanged:
`implement-local-inference-adapters`. No commit or push was made.
