"""Acquire or cache-check pinned service images, preserving the local database image."""

import re
from collections.abc import Callable, Sequence
from pathlib import Path
from subprocess import CompletedProcess

from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.service_plan import plan_services
from arxiv_int.runtime.setup.model import RETRY_COMMAND, PhaseResult, reused_or_ready
from arxiv_int.runtime.setup.state import fingerprint_for
from arxiv_int.stores.postgres.disposable import image_present as docker_image_present
from arxiv_int.stores.postgres_image.pins import load_image_pins

CommandRunner = Callable[..., CompletedProcess[str]]
LOCAL_POSTGRES_PREFIX = "arxiv-int/postgres"
_SERVICE = re.compile(r"^  ([a-z0-9-]+):$")
_IMAGE = re.compile(r"^    image:\s+(\S+)$")


def compose_service_images(project_root: Path) -> dict[str, str]:
    """Parse service image refs from the checked-in Compose file without PyYAML."""
    images: dict[str, str] = {}
    service = ""
    compose = project_root / "docker" / "compose.yaml"
    if not compose.is_file():
        return images
    for line in compose.read_text(encoding="utf-8").splitlines():
        matched_service = _SERVICE.match(line)
        if matched_service:
            service = matched_service.group(1)
            continue
        matched_image = _IMAGE.match(line)
        if matched_image and service:
            images[service] = matched_image.group(1)
    return images


def postgres_image_ref(project_root: Path) -> str:
    """Return the project-owned database image tag."""
    return load_image_pins(project_root).local_image_ref


def run_postgres_image_phase(
    project_root: Path,
    *,
    downloads: bool,
    image_present: Callable[[str], bool] = docker_image_present,
    builder: Callable[[Path], int] | None = None,
    verified: dict[str, str] | None = None,
) -> PhaseResult:
    """Reuse the pinned database image, or build it when downloads are allowed."""
    ref = postgres_image_ref(project_root)
    digest = fingerprint_for(ref)
    if image_present(ref):
        return PhaseResult(
            "postgres-image",
            reused_or_ready(verified, "postgres-image", digest),
            f"image present: {ref}",
            fingerprint=digest,
        )
    if not downloads:
        return PhaseResult(
            "postgres-image",
            "blocked",
            f"offline cache miss for {ref}",
            action="set SETUP_DOWNLOADS=1 or build with make postgres-image",
        )
    if builder is None:
        return PhaseResult(
            "postgres-image",
            "blocked",
            "postgres image builder is unavailable",
            action="make postgres-image",
        )
    if builder(project_root) != 0:
        return PhaseResult(
            "postgres-image",
            "blocked",
            "pinned postgres image build failed",
            action="make postgres-image",
        )
    return PhaseResult("postgres-image", "ready", f"built {ref}", fingerprint=digest)


def run_images_phase(
    config: RuntimeConfig,
    profiles: str | Sequence[str],
    *,
    downloads: bool,
    runner: CommandRunner,
    image_present: Callable[[str], bool] = docker_image_present,
    listed_images: dict[str, str] | None = None,
    verified: dict[str, str] | None = None,
) -> PhaseResult:
    """Pull selected non-local images, or refuse offline cache misses."""
    plan = plan_services(profiles, project_root=config.project_root)
    images = (
        listed_images if listed_images is not None else compose_service_images(config.project_root)
    )
    selected = set(plan.services)
    missing: list[str] = []
    present: list[str] = []
    for service, ref in images.items():
        if service not in selected:
            continue
        if service == "database" or ref.startswith("arxiv-int/"):
            continue
        if image_present(ref):
            present.append(ref)
            continue
        missing.append(ref)
    digest = fingerprint_for(*sorted(images.values()), *plan.services)
    if not missing:
        detail = (
            "selected service images are present" if present or not images else "no pullable images"
        )
        return PhaseResult(
            "images",
            reused_or_ready(verified, "images", digest),
            detail,
            fingerprint=digest,
        )
    if not downloads:
        return PhaseResult(
            "images",
            "blocked",
            "offline cache miss: " + ", ".join(missing[:3]),
            action="set SETUP_DOWNLOADS=1 or load the pinned images locally",
        )
    completed = runner(("docker", "compose", "pull"), cwd=config.project_root)
    if completed.returncode != 0:
        return PhaseResult(
            "images",
            "blocked",
            "service image pull failed",
            action="check registry access, then " + RETRY_COMMAND,
        )
    return PhaseResult("images", "ready", "selected service images acquired", fingerprint=digest)
