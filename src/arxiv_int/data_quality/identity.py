"""Stable rule identities shared by catalog compilers."""

from arxiv_int.contracts.sqlalchemy.normalize import NormalizedColumn


class UnsupportedQualityMappingError(ValueError):
    """Raised when a declared quality rule has no reviewed mapping."""


def rule_id(contract_id: str, column: str, kind: str, suffix: str = "") -> str:
    """Return the stable `{contract}.{column}.{kind}` rule identity."""
    tail = f".{suffix}" if suffix else ""
    return f"{contract_id}.{column}.{kind}{tail}"


def describe(column: NormalizedColumn, sentence: str) -> str:
    """Prefix a generated sentence with the retained ODCS description when present."""
    if column.description:
        return f"{column.description} {sentence}"
    return sentence
