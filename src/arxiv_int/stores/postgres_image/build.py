"""Build the project-owned ParadeDB + AGE image from pinned identities."""

import logging
import subprocess
from pathlib import Path

from arxiv_int.stores.postgres_image.pins import ImagePins, load_image_pins

_LOG = logging.getLogger(__name__)


def build_postgres_image(
    project_root: Path,
    *,
    pins: ImagePins | None = None,
    no_cache: bool = False,
) -> ImagePins:
    """Build the local image using the repository Dockerfile and pins.env."""
    resolved = pins or load_image_pins(project_root)
    command = [
        "docker",
        "build",
        "--file",
        str(project_root / "docker" / "postgres" / "Dockerfile"),
        "--tag",
        resolved.local_image_ref,
        "--build-arg",
        f"PARADEDB_IMAGE={resolved.paradedb_image}",
        "--build-arg",
        f"PARADEDB_DIGEST={resolved.paradedb_digest}",
        "--build-arg",
        f"POSTGRES_MAJOR={resolved.postgres_major}",
        "--build-arg",
        f"POSTGRES_VERSION={resolved.postgres_version}",
        "--build-arg",
        f"PG_SEARCH_VERSION={resolved.pg_search_version}",
        "--build-arg",
        f"VECTOR_VERSION={resolved.vector_version}",
        "--build-arg",
        f"AGE_GIT_SHA={resolved.age_git_sha}",
        "--build-arg",
        f"AGE_VERSION={resolved.age_version}",
        "--build-arg",
        f"IMAGE_TAG={resolved.image_tag}",
    ]
    if no_cache:
        command.append("--no-cache")
    command.append(str(project_root))
    _LOG.info("building %s", resolved.local_image_ref)
    completed = subprocess.run(command, check=False, cwd=project_root)
    if completed.returncode != 0:
        raise RuntimeError(f"docker build failed for {resolved.local_image_ref}")
    return resolved
