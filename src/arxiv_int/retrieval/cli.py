"""Dependency-light argument parsing for lexical retrieval commands."""

import argparse
from pathlib import Path

MODE_MATCH = "match"
MODE_IDENTIFIER = "identifier"


def add_search_parser(
    subcommands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Register ``arxiv-int search lexical`` over the active BM25 projection."""
    parser = subcommands.add_parser("search", help="query the active retrieval projections")
    commands = parser.add_subparsers(dest="search_command", required=True)
    lexical = commands.add_parser(
        "lexical",
        help="Russian-aware BM25 search with filters, snippets, facets and citations",
    )
    lexical.add_argument("query", help="query text, or a literal id with --mode identifier")
    lexical.add_argument(
        "--mode",
        choices=(MODE_MATCH, MODE_IDENTIFIER),
        default=MODE_MATCH,
        help="ranked match (default) or exact literal identifier lookup",
    )
    lexical.add_argument("--limit", type=int, default=10, help="number of results (default: 10)")
    lexical.add_argument("--offset", type=int, default=0, help="rank offset for paging")
    lexical.add_argument(
        "--field",
        action="append",
        default=None,
        metavar="FIELD",
        help="indexed text field to search (repeatable; default: body and title)",
    )
    lexical.add_argument("--language", default=None, help="restrict results to one language")
    lexical.add_argument("--document-id", default=None, help="restrict results to one document")
    lexical.add_argument(
        "--facet",
        action="append",
        default=None,
        metavar="FIELD",
        help="report grouped match counts for one filter field (repeatable)",
    )
    lexical.add_argument("--facet-limit", type=int, default=10)
    lexical.add_argument("--no-snippets", action="store_true", help="skip highlighted snippets")
    lexical.add_argument("--snippet-chars", type=int, default=200)
    lexical.add_argument(
        "--citations",
        action="store_true",
        help="resolve every hit to its canonical chunk source span",
    )
    lexical.add_argument(
        "--explain",
        action="store_true",
        help="report the analyzed plan, index size and in-flight index builds",
    )
    lexical.add_argument(
        "--lenient",
        action="store_true",
        help="ignore query syntax errors instead of reporting them",
    )
    lexical.add_argument("--database-url", default=None, help=argparse.SUPPRESS)
    lexical.add_argument("--json", action="store_true", help="write JSON to stdout")
    lexical.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    calibrate = commands.add_parser(
        "calibrate",
        help="compare frozen Russian tokenizer and query profiles",
    )
    calibrate.add_argument("--run-id", required=True, help="immutable evaluation run identity")
    calibrate.add_argument("--runs-dir", type=Path, default=None, help=argparse.SUPPRESS)
    calibrate.add_argument("--database-url", default=None, help=argparse.SUPPRESS)
    calibrate.add_argument("--json", action="store_true", help="write JSON to stdout")
    calibrate.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
