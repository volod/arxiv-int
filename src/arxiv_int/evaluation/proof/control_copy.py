"""Bounded disposable archive copies and path-free immutability snapshots."""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from arxiv_int.contracts.generate.normalize import normalize_json, sha256_text
from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.runtime import load_runtime_config
from arxiv_int.runtime.config_model import RuntimeConfig

CAPABILITY_ID = "pipeline-control"
MAX_COPY_FILES = 8
MAX_COPY_FILE_BYTES = 4 * 1024 * 1024
MAX_COPY_TOTAL_BYTES = 16 * 1024 * 1024
IMMUTABILITY_FILE_LIMIT = 10_000
SEED_NAME = "proof-control-seed.txt"
ADD_NAME = "proof-control-add.txt"


@dataclass(frozen=True, slots=True)
class ImmutabilitySnapshot:
    """Path-free metadata fingerprint of sampled source files."""

    file_count: int
    fingerprint: str


@dataclass(frozen=True, slots=True)
class ProofWorkspace:
    """Isolated writable roots for one pipeline-control proof."""

    work_root: Path
    copy_root: Path
    silos: tuple[SiloRoot, ...]
    config: RuntimeConfig
    source_before: ImmutabilitySnapshot


def resolve_source_silos(project_root: Path, archive_dir: Path | None) -> tuple[SiloRoot, ...]:
    """Return operator silos, or a single explicit archive root for tests."""
    if archive_dir is not None:
        return (SiloRoot("default", archive_dir.resolve()),)
    config = load_runtime_config(project_root=project_root)
    return tuple(SiloRoot(silo.silo_id, silo.root) for silo in config.archive_silos)


def snapshot_sources(
    silos: tuple[SiloRoot, ...], *, file_limit: int = IMMUTABILITY_FILE_LIMIT
) -> ImmutabilitySnapshot:
    """Hash size/mtime/inode metadata without storing paths or file bytes."""
    rows: list[str] = []
    remaining = file_limit
    for silo in silos:
        if remaining <= 0:
            break
        if not silo.root.exists():
            continue
        for path in _iter_files(silo.root):
            if remaining <= 0:
                break
            try:
                stat = path.stat()
            except OSError:
                continue
            rows.append(f"{stat.st_size}:{stat.st_mtime_ns}:{stat.st_ino}")
            remaining -= 1
    payload = {"files": len(rows), "meta": sorted(rows)}
    return ImmutabilitySnapshot(len(rows), sha256_text(normalize_json(payload)))


def prepare_workspace(
    work_root: Path,
    sources: tuple[SiloRoot, ...],
    project_root: Path,
) -> ProofWorkspace:
    """Copy a bounded file set into proof-work and isolate runtime roots."""
    work_root.mkdir(parents=True, exist_ok=True)
    copy_root = work_root / "archive"
    copy_root.mkdir(parents=True, exist_ok=True)
    before = snapshot_sources(sources)
    if before.file_count < 1:
        raise ValueError("archive silo has no readable files for pipeline-control proof")
    silos = copy_bounded(sources, copy_root)
    _ensure_seed_files(silos)
    config = isolated_config(work_root, silos[0].root, project_root)
    return ProofWorkspace(work_root, copy_root, silos, config, before)


def copy_bounded(sources: tuple[SiloRoot, ...], dest_root: Path) -> tuple[SiloRoot, ...]:
    """Copy up to MAX_COPY_FILES regular files; never write the source silos."""
    copied, remaining, _budget = _copy_pass(
        sources, dest_root, MAX_COPY_FILES, MAX_COPY_FILE_BYTES, MAX_COPY_TOTAL_BYTES
    )
    if remaining == MAX_COPY_FILES:
        copied, remaining, _budget = _copy_pass(
            sources, dest_root, MAX_COPY_FILES, MAX_COPY_TOTAL_BYTES, MAX_COPY_TOTAL_BYTES
        )
    if not copied:
        raise ValueError("pipeline-control proof copy has no archive silos")
    return tuple(copied)


def _copy_pass(
    sources: tuple[SiloRoot, ...],
    dest_root: Path,
    remaining: int,
    max_file_bytes: int,
    budget: int,
) -> tuple[list[SiloRoot], int, int]:
    copied: list[SiloRoot] = []
    for silo in sources:
        dest = dest_root / silo.silo_id
        dest.mkdir(parents=True, exist_ok=True)
        remaining, budget = _copy_silo(silo, dest, remaining, max_file_bytes, budget)
        copied.append(SiloRoot(silo.silo_id, dest))
    return copied, remaining, budget


def isolated_config(work_root: Path, archive: Path, project_root: Path) -> RuntimeConfig:
    """Build a RuntimeConfig that cannot see operator dotenv roots."""
    mapping = {
        "ARCHIVE_DIR": str(archive),
        "RESULTS_DIR": str(work_root / "results"),
        "PGDATA_DIR": str(work_root / "pgdata"),
        "RUNS_DIR": str(work_root / "runs"),
        "SERVICE_STATE_DIR": str(work_root / "services"),
        "MODEL_CACHE_DIR": str(work_root / "models"),
        "TMP_DIR": str(work_root / "tmp"),
        "DATA_DIR": str(work_root / "data"),
        "PIPELINE_PROFILE": "fixture",
    }
    for key, value in mapping.items():
        if key.endswith("_DIR") or key == "DATA_DIR":
            Path(value).mkdir(parents=True, exist_ok=True)
    return load_runtime_config(
        project_root=project_root,
        environment=mapping,
        dotenv_path=work_root / "no-dotenv",
    )


def _copy_silo(
    silo: SiloRoot, dest: Path, remaining: int, max_bytes: int, budget: int
) -> tuple[int, int]:
    for path in _iter_files(silo.root):
        if remaining <= 0 or budget <= 0:
            return remaining, budget
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > max_bytes or size > budget:
            continue
        relative = path.relative_to(silo.root)
        target = dest / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
        remaining -= 1
        budget -= size
    return remaining, budget


def _ensure_seed_files(silos: tuple[SiloRoot, ...]) -> None:
    root = silos[0].root
    files = [path for path in _iter_files(root)]
    if len(files) < 2:
        (root / SEED_NAME).write_text("pipeline-control-seed\n", encoding="ascii")


def _iter_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return
    try:
        entries = sorted(root.rglob("*"), key=lambda item: item.as_posix())
    except OSError:
        return
    for path in entries:
        if path.is_symlink() or not path.is_file():
            continue
        yield path
