"""Dependency-light argument parsing for archive locate and ledger import."""

import argparse
from pathlib import Path


def add_archive_parser(
    subcommands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Register ``arxiv-int archive locate`` and ``archive import-ledger``."""
    parser = subcommands.add_parser(
        "archive",
        help="resolve source locations and import portable path-event ledgers",
    )
    commands = parser.add_subparsers(dest="archive_command", required=True)
    locate = commands.add_parser(
        "locate",
        help="resolve a content, fact, or report citation to source locations",
    )
    locate.add_argument("token", help="document id, or fact/report id with --kind")
    locate.add_argument(
        "--kind",
        choices=("content", "fact", "report"),
        default="content",
        help="citation kind (default: content)",
    )
    locate.add_argument("--json", action="store_true", help="write JSON to stdout")
    locate.add_argument("--catalog", type=Path, default=None)
    locate.add_argument("--ledger", type=Path, default=None)
    locate.add_argument(
        "--silo",
        action="append",
        default=None,
        metavar="SILO_ID=ROOT",
        help="silo root used only to validate containment and current hashes",
    )
    locate.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    imported = commands.add_parser(
        "import-ledger",
        help="import a portable organizer path-event ledger idempotently",
    )
    imported.add_argument("source", type=Path, help="portable path-event ledger to import")
    imported.add_argument("--ledger", type=Path, default=None, help="destination ledger")
    imported.add_argument("--ledger-id", default="")
    imported.add_argument("--json", action="store_true", help="write JSON to stdout")
    imported.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
