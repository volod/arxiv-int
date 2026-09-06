"""Injectable setup boundaries for production and deterministic fakes."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from subprocess import CompletedProcess, run
from time import sleep as default_sleep

from arxiv_int.readiness.probes import LocalProbe, Probe
from arxiv_int.runtime.compose import run_compose
from arxiv_int.stores.postgres.disposable import image_present
from arxiv_int.stores.postgres_image.build import build_postgres_image


@dataclass
class CancelToken:
    """Cooperative cancellation checked between phases and wait polls."""

    cancelled: bool = False

    def cancel(self) -> None:
        self.cancelled = True

    def __call__(self) -> bool:
        return self.cancelled


def default_command_run(
    command: tuple[str, ...], *, cwd: Path, env: Mapping[str, str] | None = None
) -> CompletedProcess[str]:
    """Run one command without a shell."""
    return run(
        command,
        cwd=cwd,
        env=None if env is None else dict(env),
        check=False,
        capture_output=True,
        text=True,
    )


def default_build_image(project_root: Path) -> int:
    """Build the pinned database image and return a process status."""
    try:
        build_postgres_image(project_root)
    except (OSError, RuntimeError, ValueError):
        return 1
    return 0


@dataclass
class SetupAdapters:
    """Injectable boundaries so deterministic tests never touch the network."""

    which: Callable[[str], str | None]
    run: Callable[..., CompletedProcess[str]]
    probe: Probe
    compose: Callable[..., int] = run_compose
    image_present: Callable[[str], bool] = image_present
    build_image: Callable[[Path], int] = default_build_image
    listed_images: dict[str, str] | None = None
    listed_models: set[str] | None = None
    sleep: Callable[[float], None] = default_sleep
    cancel: CancelToken = field(default_factory=CancelToken)
    wait_seconds: float = 120.0


def production_adapters() -> SetupAdapters:
    """Return adapters bound to the local host."""
    probe = LocalProbe()
    return SetupAdapters(which=probe.which, run=default_command_run, probe=probe)
