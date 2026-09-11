"""Safe identifiers, checksums, and projection object names."""

import hashlib
import re

from arxiv_int.contracts.generate.normalize import sha256_text
from arxiv_int.transformations.credentials import sanitize_generation_id

# PostgreSQL NAMEDATALEN is 64 including the terminator, so unquoted identifiers
# are at most 63 bytes. dbt isolation names are ``<model>__g_<version>`` with a
# 32-character generation suffix; ``proj_lexical_rows__g_<uuid-run>`` is 53.
_MAX_IDENT_LEN = 63
_TOKEN = re.compile(rf"^[a-z][a-z0-9_]{{0,{_MAX_IDENT_LEN - 1}}}$")


class UnsafeIdentifierError(ValueError):
    """Raised when a composed SQL or Cypher name is not a safe token."""


def sanitize_version_id(run_id: str) -> str:
    """Return the same PostgreSQL-safe token dbt uses for generation isolation."""
    return sanitize_generation_id(run_id)


def require_ident(value: str) -> str:
    """Return ``value`` when it is a safe unquoted PostgreSQL identifier."""
    if not _TOKEN.match(value):
        raise UnsafeIdentifierError(f"unsafe identifier: {value!r}")
    return value


def projection_id(kind: str, version_id: str) -> str:
    """Return the stable metadata primary key for one kind and version."""
    return f"{require_ident(kind)}:{require_ident(version_id)}"


def table_name(kind: str, version_id: str, *, suffix: str = "") -> str:
    """Return an unqualified search-schema table name for one versioned object."""
    base = f"{require_ident(kind)}_p_{require_ident(version_id)}"
    if suffix:
        return f"{base}_{require_ident(suffix)}"
    return base


def qualified_table(kind: str, version_id: str, *, suffix: str = "") -> str:
    """Return ``search.<table>`` for a versioned projection relation."""
    return f"search.{table_name(kind, version_id, suffix=suffix)}"


def age_graph_name(version_id: str) -> str:
    """Return an AGE graph name for one version."""
    return f"g_{require_ident(version_id)}"


def derived_relation(model: str, version_id: str) -> str:
    """Return the isolated dbt generation table for one projection model."""
    return f"derived.{require_ident(model)}__g_{require_ident(version_id)}"


def logical_checksum(ids: list[str] | tuple[str, ...]) -> str:
    """Fingerprint sorted logical ids so rebuilds can prove identity stability."""
    ordered = sorted({item for item in ids if item})
    return sha256_text("|".join(ordered))


def evidence_id(projection: str, check_name: str) -> str:
    """Return a stable evidence row id without embedding paths."""
    digest = hashlib.sha256(f"{projection}:{check_name}".encode()).hexdigest()
    return digest[:32]


def cypher_string(value: str) -> str:
    """Escape a compact display property for a Cypher string literal."""
    return value.replace("\\", "\\\\").replace("'", "\\'")
