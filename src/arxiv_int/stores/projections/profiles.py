"""Per-kind engine profile identities bound into a projection's input fingerprint.

A projection version id is derived from the run, not from the engine settings that shaped its
index, so the registry alone cannot say which tokenizer or index profile built an active
projection. Binding the profile into ``ctl.projections.input_fingerprint`` lets a reader recompute
the expected value and refuse a projection that a different profile produced.
"""

from arxiv_int.contracts.generate.normalize import sha256_text
from arxiv_int.stores.projections.adapters.lexical import TOKENIZER_FINGERPRINT
from arxiv_int.stores.projections.model import KIND_GRAPH, KIND_LEXICAL, KIND_VECTOR

# Vector and graph builds carry no declared settings profile yet; their literals change only
# when one is introduced, so an unchanged build keeps its fingerprint.
VECTOR_PROFILE = "pgvector-candidate-v1"
GRAPH_PROFILE = "age-property-graph-v1"
_PROFILES: dict[str, str] = {
    KIND_LEXICAL: TOKENIZER_FINGERPRINT,
    KIND_VECTOR: VECTOR_PROFILE,
    KIND_GRAPH: GRAPH_PROFILE,
}


def engine_profile(kind: str) -> str:
    """Return the current engine profile identity for one projection kind."""
    try:
        return _PROFILES[kind]
    except KeyError as error:
        known = ", ".join(sorted(_PROFILES))
        raise ValueError(f"unknown projection kind {kind!r}; expected {known}") from error


def projection_input_fingerprint(kind: str, version_id: str, checksum: str) -> str:
    """Return the registry input fingerprint for one built projection version."""
    return sha256_text(f"{kind}|{version_id}|{checksum}|{engine_profile(kind)}")
