"""Archive-appropriate lexical probes against the active ParadeDB projection."""

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import Connection, text

from arxiv_int.evaluation.scoring.accuracy import percentile
from arxiv_int.retrieval.citations import resolve_citations, unresolved_citations
from arxiv_int.retrieval.lexical import START_TAG, LexicalRequest, explain, lookup, search
from arxiv_int.retrieval.lexical_model import LexicalHit
from arxiv_int.retrieval.metrics import RetrievalCase, evaluate_retrieval
from arxiv_int.retrieval.projection import LexicalTarget, index_size
from arxiv_int.retrieval.query_normalization import SELECTED_QUERY_PROFILE
from arxiv_int.stores.projections.adapters.lexical import TOKENIZER_FINGERPRINT
from arxiv_int.stores.projections.ids import require_ident
from tests.integration.corpus.artifacts import require
from tests.integration.lexical.checks import (
    DECLARED_QUERY_KINDS,
    KNOWN_ITEM_K,
    KNOWN_ITEM_MIN_CASES,
    LATENCY_P95_MS_MAX,
    MAX_COMMON_HITS,
    MISSING_IDENTIFIER,
    PAGE_LIMIT,
    filter_matches,
    gold_span,
    identifier_exactness,
    limit_honored,
    offset_matches,
    probe_terms,
    retrieved_chunks,
)

_SAMPLE_SQL = (
    "SELECT p.chunk_id, p.document_id, p.language, p.body, c.start_char, c.end_char "
    "FROM {relation} p JOIN corpus.chunks c ON c.chunk_id = p.chunk_id "
    "WHERE length(p.body) BETWEEN 24 AND 800 ORDER BY p.chunk_id LIMIT 80"
)


def prove_queries(connection: Connection, target: LexicalTarget) -> dict[str, Any]:
    """Run the declared query kinds and return path-free metric evidence."""
    require(target.tokenizer_fingerprint == TOKENIZER_FINGERPRINT, "tokenizer fingerprint drifted")
    samples = _samples(connection, target.table)
    require(bool(samples), "active projection has no sampled chunks")
    cases, latencies, exact, term, document_id = _known_items(connection, samples)
    require(len(cases) >= KNOWN_ITEM_MIN_CASES, "too few known-item probes succeeded")
    metrics = evaluate_retrieval(cases, k=KNOWN_ITEM_K)
    require(metrics.recall_at_k == 1.0, "known-item recall@10 is below the declared gate")
    require(metrics.span_intact_at_k == 1.0, "known-item citations are not intact")
    require(exact == 1.0, "identifier lookup missed a sampled chunk")
    filtered = search(connection, LexicalRequest(query=term, document_id=document_id))
    require(filter_matches(filtered.hits, document_id=document_id), "document filter leaked")
    latencies.append(filtered.elapsed_ms)
    _smoke(connection, term, latencies)
    require(
        filtered.query_profile == SELECTED_QUERY_PROFILE, "selected query profile was not served"
    )
    p95 = percentile(tuple(latencies), 95.0)
    require(p95 <= LATENCY_P95_MS_MAX, "p95 query latency exceeded the smoke bound")
    sizes = index_size(connection, target)
    require(sizes["index_bytes"] > 0 and sizes["table_bytes"] > 0, "index size evidence is missing")
    return {
        "declaredQueryKinds": list(DECLARED_QUERY_KINDS),
        "identifierExactness": exact,
        "indexAmplification": round(sizes["index_bytes"] / sizes["table_bytes"], 6),
        "indexBytes": int(sizes["index_bytes"]),
        "knownItemCases": metrics.count,
        "latencyP95Ms": p95,
        "meanReciprocalRank": metrics.mean_reciprocal_rank,
        "queryProfile": SELECTED_QUERY_PROFILE,
        "recallAtK": metrics.recall_at_k,
        "spanIntactAtK": metrics.span_intact_at_k,
        "tableBytes": int(sizes["table_bytes"]),
        "unresolvedCitations": 0,
    }


def _smoke(connection: Connection, term: str, latencies: list[float]) -> None:
    faceted = search(connection, LexicalRequest(query=term, facets=("language",)))
    require(bool(faceted.facets.get("language")), "language facet was empty")
    latencies.append(faceted.elapsed_ms)
    limited = search(connection, LexicalRequest(query=term, limit=PAGE_LIMIT))
    require(limit_honored(len(limited.hits), limited.total, PAGE_LIMIT), "limit was not honored")
    latencies.append(limited.elapsed_ms)
    if limited.total >= 2:
        paged = search(connection, LexicalRequest(query=term, limit=1, offset=1))
        require(offset_matches(limited.hits, paged.hits), "offset did not select the second hit")
        latencies.append(paged.elapsed_ms)
    plan = "\n".join(explain(connection, LexicalRequest(query=term)))
    require("ParadeDB" in plan or "paradedb" in plan.lower(), "explain plan is not a ParadeDB plan")
    require(lookup(connection, MISSING_IDENTIFIER) == (), "missing identifier returned a hit")
    citations = resolve_citations(connection, _hit_ids(limited.hits))
    require(unresolved_citations(_hit_ids(limited.hits), citations) == (), "citations unresolved")
    _require_snippets(limited.hits)


def _samples(connection: Connection, table: str) -> tuple[dict[str, Any], ...]:
    schema, _, name = table.partition(".")
    relation = f"{require_ident(schema)}.{require_ident(name)}"
    rows = connection.execute(text(_SAMPLE_SQL.format(relation=relation))).mappings().all()
    ordered = sorted(rows, key=lambda row: (str(row["language"]) != "rus", str(row["chunk_id"])))
    return tuple(dict(row) for row in ordered)


def _known_items(
    connection: Connection, samples: Sequence[Mapping[str, Any]]
) -> tuple[tuple[RetrievalCase, ...], list[float], float, str, str]:
    cases: list[RetrievalCase] = []
    latencies: list[float] = []
    exact_scores: list[float] = []
    term = ""
    document_id = ""
    for sample in samples:
        if len(cases) >= KNOWN_ITEM_MIN_CASES:
            break
        case, elapsed, used = _one_known_item(connection, sample)
        if case is None or used is None:
            continue
        cases.append(case)
        latencies.append(elapsed)
        term, document_id = used, str(sample["document_id"])
        found = lookup(connection, str(sample["chunk_id"]))
        exact_scores.append(
            identifier_exactness(found, str(sample["chunk_id"]), str(sample["document_id"]))
        )
        cited = resolve_citations(connection, [str(sample["chunk_id"])])
        require(unresolved_citations([str(sample["chunk_id"])], cited) == (), "source span missing")
    exact = sum(exact_scores) / len(exact_scores) if exact_scores else 0.0
    require(bool(term) and bool(document_id), "known-item probes produced no filter term")
    return tuple(cases), latencies, exact, term, document_id


def _one_known_item(
    connection: Connection, sample: Mapping[str, Any]
) -> tuple[RetrievalCase | None, float, str | None]:
    span = gold_span(str(sample["document_id"]), int(sample["start_char"]), int(sample["end_char"]))
    for term in probe_terms(str(sample["body"])):
        ranked = search(connection, LexicalRequest(query=term, limit=KNOWN_ITEM_K))
        if ranked.total == 0 or ranked.total > MAX_COMMON_HITS:
            continue
        citations = resolve_citations(connection, _hit_ids(ranked.hits))
        if unresolved_citations(_hit_ids(ranked.hits), citations):
            continue
        case = RetrievalCase(retrieved_chunks(ranked.hits, citations), (span,))
        if evaluate_retrieval((case,), k=KNOWN_ITEM_K).recall_at_k == 1.0:
            return case, ranked.elapsed_ms, term
    return None, 0.0, None


def _hit_ids(hits: Sequence[LexicalHit]) -> list[str]:
    return [hit.chunk_id for hit in hits]


def _require_snippets(hits: Sequence[LexicalHit]) -> None:
    require(bool(hits), "limit query returned no hits")
    require(any(START_TAG in hit.snippet for hit in hits if hit.snippet), "snippets were missing")
