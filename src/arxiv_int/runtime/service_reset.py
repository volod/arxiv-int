"""Stop-preserving vs destructive service-data reset helpers."""

import logging
import shutil
from pathlib import Path

from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.containment import containment_violation, erase_protected_roots

_LOG = logging.getLogger(__name__)


class ServiceResetError(ValueError):
    """A service-data reset target is unsafe or incomplete."""


def _configured_data_paths(config: RuntimeConfig) -> tuple[Path, ...]:
    """Return the configured, still unresolved host roots Compose services write."""
    paths = [
        config.pgdata_dir,
        config.service_state_dir,
        config.model_cache_dir,
    ]
    if config.pg_wal_dir is not None:
        paths.append(config.pg_wal_dir)
    paths.extend(path for _, path in config.pg_tablespaces)
    unique: dict[Path, Path] = {}
    for path in paths:
        unique.setdefault(path.expanduser().resolve(), path)
    return tuple(unique[key] for key in sorted(unique, key=str))


def service_data_targets(config: RuntimeConfig) -> tuple[Path, ...]:
    """Return resolved host roots Compose services write that a reset may erase."""
    return tuple(path.expanduser().resolve() for path in _configured_data_paths(config))


def _assert_erasable(config: RuntimeConfig, target: Path) -> Path:
    """Resolve one configured target now and refuse every protected placement."""
    resolved = target.expanduser().resolve()
    if resolved == Path(resolved.anchor):
        raise ServiceResetError(f"refusing to erase filesystem root for {target}")
    violation = containment_violation(resolved, erase_protected_roots(config))
    if violation is not None:
        raise ServiceResetError(
            f"refusing to erase {resolved}; it overlaps {violation.detail} "
            f"({violation.variable}); change that root in .env"
        )
    if resolved not in service_data_targets(config):
        raise ServiceResetError(f"refusing to erase unlisted path {resolved}")
    return resolved


def validate_service_reset(config: RuntimeConfig) -> tuple[Path, ...]:
    """Resolve and accept every reset target, or refuse before any service is stopped."""
    return tuple(_assert_erasable(config, path) for path in _configured_data_paths(config))


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


def _erase(config: RuntimeConfig, configured: Path) -> None:
    """Revalidate immediately before deletion so a swapped link cannot widen the target."""
    path = _assert_erasable(config, configured)
    _clear_directory(path)
    database = path == config.pgdata_dir.expanduser().resolve()
    path.mkdir(mode=0o700 if database else 0o755, parents=True, exist_ok=True)
    if database:
        path.chmod(0o700)
    _LOG.info("erased service data: %s", path)


def reset_service_data(config: RuntimeConfig, *, apply: bool) -> tuple[Path, ...]:
    """Stop-safe wipe of service data roots; dry-run unless apply is true."""
    configured = _configured_data_paths(config)
    targets = validate_service_reset(config)
    if not apply:
        for path in targets:
            _LOG.info("reset dry-run would erase: %s", path)
        _LOG.info("re-run with --apply (or APPLY=1) to erase service data after stop")
        return targets
    for path in configured:
        _erase(config, path)
    return targets
