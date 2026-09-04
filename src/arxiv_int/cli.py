"""Command-line entrypoint for arxiv-int."""

import argparse
import logging
from collections.abc import Sequence

from arxiv_int.features import inventory_lines
from arxiv_int.metadata import project_info

_LOG = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the command parser independently for tests and future subcommands."""
    parser = argparse.ArgumentParser(prog="arxiv-int")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("info", help="show the installed project identity")
    features = subcommands.add_parser("features", help="show optional feature groups")
    features.add_argument("--stage", default=None, help="only groups one pipeline stage needs")
    return parser


def _run_info() -> int:
    info = project_info()
    _LOG.info("%s %s (%s)", info.distribution, info.version, info.package)
    return 0


def _run_features(stage: str | None) -> int:
    try:
        lines = inventory_lines(stage)
    except LookupError as error:
        _LOG.error("%s", error)
        return 1
    for line in lines:
        _LOG.info("%s", line)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the selected command and return a process status."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = build_parser().parse_args(argv)
    if args.command == "features":
        return _run_features(args.stage)
    return _run_info()


if __name__ == "__main__":
    raise SystemExit(main())
