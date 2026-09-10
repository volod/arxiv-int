"""Resolve a run id, latest generation, or dataset without mutating artifacts."""

from dataclasses import dataclass
from pathlib import Path

from arxiv_int.inspect.model import DEVELOPMENT_ALIASES, KIND_DATASET, KIND_RUN, LATEST_TOKEN
from arxiv_int.pipeline.run.persist import CONTEXT_NAME, STATUS_NAME, StageExecution, load_status


class InspectError(RuntimeError):
    """Operator-visible inspection refusal."""

    exit_code = 1


@dataclass(frozen=True, slots=True)
class InspectionTarget:
    """Resolved inspect subject: one frozen run, one dataset, or both."""

    kind: str
    target: str
    run_id: str
    dataset: str


def latest_run_id(runs_dir: Path) -> str | None:
    """Return the newest ``run-*`` directory that still has frozen context."""
    found = list(runs_dir.glob("run-*/" + CONTEXT_NAME))
    if not found:
        return None
    return max(found, key=lambda path: path.stat().st_mtime).parent.name


def resolve_target(
    token: str, runs_dir: Path, *, dataset_hint: str | None = None
) -> InspectionTarget:
    """Map ``RUN_ID|DATASET|latest`` onto a frozen run and optional dataset filter."""
    target = token.strip()
    if not target:
        raise InspectError("inspect requires a run id, dataset id, or latest")
    if target.lower() in DEVELOPMENT_ALIASES:
        raise InspectError("refusing developer alias; use the id from arxiv-int run create")
    if target == LATEST_TOKEN:
        run_id = latest_run_id(runs_dir)
        if run_id is None:
            raise InspectError("no run to inspect; create a run first")
        return InspectionTarget(KIND_RUN, target, run_id, dataset_hint or "")
    context_path = runs_dir / target / CONTEXT_NAME
    if context_path.is_file():
        return InspectionTarget(KIND_RUN, target, target, dataset_hint or "")
    run_id = latest_run_id(runs_dir) or ""
    return InspectionTarget(KIND_DATASET, target, run_id, target)


def relative_posix(path: Path, root: Path) -> str:
    """Return a root-relative POSIX path, or a placeholder outside the root."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return "<path>"


def attempt_locations(runs_dir: Path, run_id: str) -> tuple[Path, ...]:
    """Return attempt directories from status.json, then a manifests walk."""
    seen: list[Path] = list(ledger_attempts(runs_dir, run_id))
    manifests = runs_dir / run_id / "manifests"
    if manifests.is_dir():
        for path in sorted(manifests.glob("*/*/attempt-*")):
            if path.is_dir() and (path / "manifest.json").is_file() and path not in seen:
                seen.append(path)
    return tuple(seen)


def ledger_attempts(runs_dir: Path, run_id: str) -> dict[Path, StageExecution]:
    """Map each readable attempt directory onto the ledger row that actually claims it.

    Superseded attempts stay absent, so a retried stage never reports an earlier
    attempt with the accepted attempt's number, status, or cache decision.
    """
    claimed: dict[Path, StageExecution] = {}
    if not (runs_dir / run_id / STATUS_NAME).is_file():
        return claimed
    for item in load_status(runs_dir, run_id).executions:
        directory = _execution_directory(item, runs_dir)
        if directory is not None:
            claimed[directory] = item
    return claimed


def _execution_directory(item: StageExecution, runs_dir: Path) -> Path | None:
    if not item.directory:
        return None
    raw = Path(item.directory)
    if raw.is_dir():
        return raw
    relative = runs_dir / item.directory
    return relative if relative.is_dir() else None


def lake_root(results_dir: Path) -> Path:
    """Return ``$RESULTS_DIR/normalized``."""
    return results_dir / "normalized"


def lake_dataset_dir(results_dir: Path, dataset: str) -> Path:
    """Return ``$RESULTS_DIR/normalized/<dataset>``."""
    return lake_root(results_dir) / dataset
