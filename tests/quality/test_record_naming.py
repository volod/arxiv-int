"""Record filename sequence and group parsing."""

from pathlib import Path

import pytest

from arxiv_int.quality.record_naming import (
    build_record_filename,
    next_record_sequence,
    parse_record_stem,
    record_identifier_from_stem,
)


def test_parse_sequenced_stem_prefers_longest_group() -> None:
    parsed = parse_record_stem(
        "0009-contract-gov-refactor-contract-identity-and-reference-validation"
    )
    assert parsed is not None
    assert parsed.sequence == 9
    assert parsed.group == "contract-gov"
    assert parsed.task_id == "refactor-contract-identity-and-reference-validation"


def test_bare_stem_is_the_task_id() -> None:
    assert parse_record_stem("earlier-work") is None
    assert record_identifier_from_stem("earlier-work") == "earlier-work"
    assert (
        record_identifier_from_stem("0011-contract-gov-implement-deterministic-schema-generation")
        == "implement-deterministic-schema-generation"
    )


def test_next_sequence_and_filename_builder(tmp_path: Path) -> None:
    (tmp_path / "0003-runtime-refactor-safe-runtime-root-boundaries.md").write_text("x")
    assert next_record_sequence(tmp_path) == 4
    assert (
        build_record_filename(4, "contract-governance", "enforce-evolution-and-migration-policy")
        == "0004-contract-gov-enforce-evolution-and-migration-policy.md"
    )


def test_unknown_capability_rejects_filename_build() -> None:
    with pytest.raises(KeyError, match="no record group abbrev"):
        build_record_filename(1, "not-a-capability", "some-task")
