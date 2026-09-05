"""Stop-preserving vs destructive service-data reset helpers."""

import logging
import shutil
from pathlib import Path

from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.paths import resolve_allowed_path

_LOG = logging.getLogger(__name__)


class ServiceResetError(ValueError):
    """A service-data reset target is unsafe or incomplete."""


def service_data_targets(config: RuntimeConfig) -> tuple[Path, ...]:
    """Return host roots Compose services write that a reset may erase."""
    targets = [
        config.pgdata_dir,
        config.service_state_dir,
        config.model_cache_dir,
    ]
    if config.pg_wal_dir is not None:
        targets.append(config.pg_wal_dir)
    targets.extend(path for _, path in config.pg_tablespaces)
    unique = {path.resolve(): path.resolve() for path in targets}
    return tuple(sorted(unique.values(), key=str))


def _assert_erasable(config: RuntimeConfig, target: Path) -> Path:
    resolved = target.expanduser().resolve()
    if resolved == Path(resolved.anchor):
        raise ServiceResetError(f"refusing to erase filesystem root for {target}")
    if resolve_allowed_path(resolved, (config.project_root,), kind="any") is not None:
        raise ServiceResetError(f"refusing to erase checkout path {resolved}")
    if resolved == config.results_dir.resolve():
        raise ServiceResetError(
            "refusing to erase RESULTS_DIR; point SERVICE_STATE_DIR at a services child"
        )
    for silo in config.archive_silos:
        if resolve_allowed_path(resolved, (silo.root,), kind="any") is not None:
            raise ServiceResetError(f"refusing to erase archive silo path {resolved}")
    if config.proof_archive_dir is not None:
        proof = config.proof_archive_dir.resolve()
        if resolved == proof or proof in resolved.parents or resolved in proof.parents:
            raise ServiceResetError(f"refusing to erase proof archive path {resolved}")
    allowed = service_data_targets(config)
    if resolved not in {path.resolve() for path in allowed}:
        raise ServiceResetError(f"refusing to erase unlisted path {resolved}")
    return resolved


def _clear_directory(path: Path) -> None:
    """Delete directory contents without following links out of the tree."""
    if not path.exists():
        return
    if path.is_symlink() or not path.is_dir():
        raise ServiceResetError(f"service data target must be a real directory: {path}")
    for child in path.iterdir():
        if child.is_symlink() or child.is_file():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def reset_service_data(config: RuntimeConfig, *, apply: bool) -> tuple[Path, ...]:
    """Stop-safe wipe of service data roots; dry-run unless apply is true."""
    targets = tuple(_assert_erasable(config, path) for path in service_data_targets(config))
    if not apply:
        for path in targets:
            _LOG.info("reset dry-run would erase: %s", path)
        _LOG.info("re-run with --apply (or APPLY=1) to erase service data after stop")
        return targets
    for path in targets:
        _clear_directory(path)
        mode = 0o700 if path == config.pgdata_dir.resolve() else 0o755
        path.mkdir(mode=mode, parents=True, exist_ok=True)
        if path == config.pgdata_dir.resolve():
            path.chmod(0o700)
        _LOG.info("erased service data: %s", path)
    return targets
