"""Run-scoped classification artifact locations and shared command plumbing."""

import argparse
import importlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CLASSIFICATION_DIRNAME = "classification"
SCHEME_DIRNAME = "scheme"
EVALUATION_DIRNAME = "evaluation"
REVIEW_PACKET = ("review", "classification")
_SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


def safe_id(value: str, label: str) -> str:
    """Return a run or label-set id that is one safe path component."""
    if _SAFE_ID.fullmatch(value) is None or ".." in value:
        raise ValueError(f"{label} must be a path-safe id: {value!r}")
    return value


@dataclass(frozen=True, slots=True)
class ClassificationLayout:
    """``$RUNS_DIR/<run-id>/classification/`` plus the run's review packet directory."""

    run_root: Path

    @classmethod
    def for_run(cls, runs_dir: Path, run_id: str) -> "ClassificationLayout":
        return cls(runs_dir / safe_id(run_id, "run id"))

    @property
    def root(self) -> Path:
        return self.run_root / CLASSIFICATION_DIRNAME

    @property
    def scheme(self) -> Path:
        return self.root / SCHEME_DIRNAME

    @property
    def review(self) -> Path:
        return self.run_root.joinpath(*REVIEW_PACKET)

    def evaluation(self, label_set: str) -> Path:
        return self.root / EVALUATION_DIRNAME / safe_id(label_set, "label set")

    def quality_evaluation(self, label_set: str) -> Path:
        """Return the classifier-quality root required by the implementation plan."""
        return (
            self.run_root
            / EVALUATION_DIRNAME
            / CLASSIFICATION_DIRNAME
            / safe_id(label_set, "label set")
        )


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    """Write rows as sorted-key ASCII JSON lines."""
    lines = "".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in rows)
    path.write_text(lines, encoding="ascii")


def command_roots(args: argparse.Namespace) -> tuple[Path, Path]:
    """Return the project root and the runs directory for one command."""
    if args.runs_dir is not None:
        from arxiv_int.runtime.project_root import find_project_root

        return find_project_root(args.project_root), Path(args.runs_dir)
    from arxiv_int.runtime.config import load_runtime_config

    config = load_runtime_config(project_root=args.project_root)
    return config.project_root, config.runs_dir


def scheme_directory(args: argparse.Namespace, runs_dir: Path) -> Path:
    """Return ``--scheme`` or the run's scheme snapshot directory."""
    if args.scheme is not None:
        return Path(args.scheme)
    if args.run_id is None:
        raise ValueError("give --scheme or --run-id")
    return ClassificationLayout.for_run(runs_dir, args.run_id).scheme


def validate_contract_rows(
    project_root: Path, contract_id: str, rows: Iterable[Mapping[str, Any]]
) -> None:
    """Validate rows against the generated contract schema and batch rules before publishing."""
    from arxiv_int.features import require_module
    from arxiv_int.pipeline.lake.validate import ContractBatchValidator

    require_module("pandera")
    pandera_errors = importlib.import_module("pandera.errors")
    try:
        ContractBatchValidator(project_root, contract_id).batch([dict(row) for row in rows])
    except (pandera_errors.SchemaError, pandera_errors.SchemaErrors) as error:
        raise ValueError(f"{contract_id} contract validation failed: {error}") from error
