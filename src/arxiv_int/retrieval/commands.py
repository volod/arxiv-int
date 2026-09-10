"""CLI handler for ``arxiv-int search lexical``."""

import argparse
import logging
import sys
from collections.abc import Iterator, Mapping
from typing import Any

from sqlalchemy import Connection, create_engine
from sqlalchemy.exc import SQLAlchemyError

from arxiv_int.contracts.generate.normalize import normalize_json
from arxiv_int.retrieval.citations import resolve_citations, unresolved_citations
from arxiv_int.retrieval.cli import MODE_IDENTIFIER
from arxiv_int.retrieval.lexical import (
    LexicalHit,
    LexicalRequest,
    LexicalResult,
    explain,
    lookup,
    search,
)
from arxiv_int.retrieval.projection import (
    LexicalQueryError,
    LexicalUnavailableError,
    concurrent_builds,
    index_size,
)
from arxiv_int.stores.projections.adapters.lexical_search import (
    SEARCH_FIELDS,
    LexicalFieldError,
)

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_UNAVAILABLE = 2
_LOG = logging.getLogger(__name__)


def run_search_command(args: argparse.Namespace) -> int:
    """Run one read-only lexical query against the active projection."""
    try:
        return _run_lexical(args)
    except LexicalUnavailableError as error:
        _LOG.error("%s", error)
        return EXIT_UNAVAILABLE
    except (LexicalFieldError, LexicalQueryError, SQLAlchemyError, OSError, RuntimeError) as error:
        _LOG.error("%s", error)
        return EXIT_FAILED


def _run_lexical(args: argparse.Namespace) -> int:
    from arxiv_int.runtime.project_root import find_project_root
    from arxiv_int.stores.postgres.selection import store_database_url

    project_root = args.project_root or find_project_root()
    url = str(args.database_url or "") or store_database_url(project_root)
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            payload = _payload(connection, args)
    finally:
        engine.dispose()
    if bool(args.json):
        sys.stdout.write(normalize_json(payload))
    else:
        for line in _console_lines(payload):
            _LOG.info("%s", line)
    if str(args.mode) == MODE_IDENTIFIER and not payload["hits"]:
        return EXIT_FAILED
    return EXIT_OK


def _payload(connection: Connection, args: argparse.Namespace) -> dict[str, Any]:
    if str(args.mode) == MODE_IDENTIFIER:
        hits = lookup(connection, str(args.query), limit=int(args.limit))
        payload: dict[str, Any] = {
            "hits": [hit.as_json_dict() for hit in hits],
            "mode": MODE_IDENTIFIER,
            "total": len(hits),
        }
    else:
        result = search(connection, _request(args))
        payload = {"mode": "match", **result.as_json_dict()}
        hits = result.hits
        if bool(args.explain):
            payload["diagnostics"] = _diagnostics(connection, args, result)
    if bool(args.citations):
        payload["citations"] = _citations(connection, hits)
    return payload


def _request(args: argparse.Namespace) -> LexicalRequest:
    fields = tuple(args.field) if args.field else SEARCH_FIELDS
    return LexicalRequest(
        query=str(args.query),
        limit=int(args.limit),
        offset=int(args.offset),
        fields=fields,
        language=args.language,
        document_id=args.document_id,
        snippets=not bool(args.no_snippets),
        snippet_chars=int(args.snippet_chars),
        facets=tuple(args.facet) if args.facet else (),
        facet_limit=int(args.facet_limit),
        lenient=bool(args.lenient),
    )


def _diagnostics(
    connection: Connection, args: argparse.Namespace, result: LexicalResult
) -> dict[str, Any]:
    return {
        "concurrentIndexBuilds": [dict(item) for item in concurrent_builds(connection)],
        "indexBytes": dict(index_size(connection, result.target)),
        "plan": list(explain(connection, _request(args), target=result.target)),
    }


def _citations(connection: Connection, hits: tuple[LexicalHit, ...]) -> dict[str, Any]:
    identifiers = [hit.chunk_id for hit in hits]
    resolved = resolve_citations(connection, identifiers)
    return {
        "resolved": [item.as_json_dict() for item in resolved],
        "unresolved": list(unresolved_citations(identifiers, resolved)),
    }


def _console_lines(payload: Mapping[str, Any]) -> Iterator[str]:
    projection = payload.get("projection") or {}
    if projection:
        yield (
            f"projection {projection['projectionId']} rows={projection['rowCount']} "
            f"index={projection['index']}"
        )
    yield f"matched {payload['total']} chunk(s); showing {len(payload['hits'])}"
    for hit in payload["hits"]:
        yield f"{hit['rank']:>4} {hit['score']:.4f} {hit['chunkId']} {hit['documentId']}"
        if hit.get("snippet"):
            yield f"      {hit['snippet']}"
    for name, values in sorted((payload.get("facets") or {}).items()):
        rendered = ", ".join(f"{item['value']}={item['matched']}" for item in values)
        yield f"facet {name}: {rendered}"
    for item in (payload.get("citations") or {}).get("resolved", []):
        yield (
            f"citation {item['chunkId']} -> {item['documentId']}"
            f"[{item['startChar']}:{item['endChar']}]"
        )
    for item in (payload.get("citations") or {}).get("unresolved", []):
        yield f"citation {item} -> unresolved"
    diagnostics = payload.get("diagnostics") or {}
    for line in diagnostics.get("plan", []):
        yield f"plan {line}"
    for item in diagnostics.get("concurrentIndexBuilds", []):
        yield f"index build pid={item['pid']} state={item['state']} wait={item['wait']}"
    if diagnostics:
        sizes = diagnostics["indexBytes"]
        yield f"index bytes={sizes['index_bytes']} table bytes={sizes['table_bytes']}"
