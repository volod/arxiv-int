"""Disposable pinned-store handle with a published local port."""

import logging
import os
import shutil
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from arxiv_int.stores.postgres_image.pins import ImagePins, load_image_pins
from arxiv_int.stores.postgres_image.probe_steps import wait_ready
from arxiv_int.stores.postgres_image.probes import disposable_database_run_args

_LOG = logging.getLogger(__name__)

DEFAULT_USER = "arxiv_int"
DEFAULT_DATABASE = "arxiv_int"
DEFAULT_PASSWORD = "schema-secret"


@dataclass(frozen=True, slots=True)
class DisposableStore:
    """Running disposable database reachable over loopback."""

    container: str
    url: str
    pgdata_dir: Path
    image_ref: str
    user: str
    database: str
    password: str


def image_present(image_ref: str) -> bool:
    """Return whether the pinned local image exists."""
    if shutil.which("docker") is None:
        return False
    result = subprocess.run(
        ["docker", "image", "inspect", image_ref],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _published_port(container: str) -> str:
    result = subprocess.run(
        ["docker", "port", container, "5432/tcp"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(result.stderr.strip() or "docker port mapping was empty")
    line = result.stdout.strip().splitlines()[0]
    _host, _, port = line.rpartition(":")
    if not port:
        raise RuntimeError(f"unparsed docker port mapping: {line}")
    return port.strip()


def _build_url(user: str, password: str, port: str, database: str) -> str:
    safe = quote(password, safe="")
    return f"postgresql+psycopg://{user}:{safe}@127.0.0.1:{port}/{database}"


@contextmanager
def disposable_store(
    project_root: Path,
    pgdata_dir: Path,
    *,
    pins: ImagePins | None = None,
    password: str = DEFAULT_PASSWORD,
    user: str = DEFAULT_USER,
    database: str = DEFAULT_DATABASE,
) -> Iterator[DisposableStore]:
    """Start one published disposable database and tear it down afterwards."""
    if shutil.which("docker") is None:
        raise RuntimeError("docker unavailable")
    resolved = pins or load_image_pins(project_root)
    if not image_present(resolved.local_image_ref):
        raise RuntimeError(f"image {resolved.local_image_ref} is not present; build it first")
    pgdata_dir.mkdir(parents=True, exist_ok=True)
    container = f"arxiv-int-schema-{os.getpid()}-{int(time.time()) % 100000}"
    common = disposable_database_run_args(
        container=container,
        image_ref=resolved.local_image_ref,
        pgdata_dir=pgdata_dir,
        password=password,
        db_user=user,
        database=database,
    )
    start = [*common[:-1], "-p", "127.0.0.1:0:5432", "-d", common[-1]]
    try:
        started = subprocess.run(start, check=False, capture_output=True, text=True)
        if started.returncode != 0:
            raise RuntimeError(started.stderr.strip() or "failed to start disposable database")
        if not wait_ready(container, user, database):
            raise RuntimeError("disposable database did not become ready")
        url = _build_url(user, password, _published_port(container), database)
        _LOG.info("disposable schema store listening on loopback")
        yield DisposableStore(
            container=container,
            url=url,
            pgdata_dir=pgdata_dir,
            image_ref=resolved.local_image_ref,
            user=user,
            database=database,
            password=password,
        )
    finally:
        subprocess.run(
            ["docker", "rm", "-f", container], check=False, capture_output=True, text=True
        )
