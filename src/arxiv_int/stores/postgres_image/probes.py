"""Disposable extension coexistence probes for the project PostgreSQL image."""

import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

from arxiv_int.runtime.host_identity import docker_user_args, host_user_spec
from arxiv_int.stores.postgres_image.pins import ImagePins, load_image_pins
from arxiv_int.stores.postgres_image.probe_model import ProbeReport
from arxiv_int.stores.postgres_image.probe_steps import (
    BM25_VECTOR_SQL,
    CYPHER_SQL,
    TXN_SQL,
    check_licenses,
    probe_dump_restore,
    probe_named,
    probe_restart,
    probe_versions,
    wait_ready,
)

_LOG = logging.getLogger(__name__)

__all__ = ["ProbeReport", "disposable_database_run_args", "run_extension_probes"]


def disposable_database_run_args(
    *,
    container: str,
    image_ref: str,
    pgdata_dir: Path,
    password: str,
    db_user: str,
    database: str,
) -> list[str]:
    """Build ``docker run`` args that keep bind-mounted PGDATA host-owned."""
    return [
        "docker",
        "run",
        "--rm",
        *docker_user_args(),
        "--name",
        container,
        "-e",
        f"POSTGRES_PASSWORD={password}",
        "-e",
        f"POSTGRES_USER={db_user}",
        "-e",
        f"POSTGRES_DB={database}",
        "-e",
        "PDB_TUNE=false",
        "-v",
        f"{pgdata_dir}:/var/lib/postgresql/data",
        image_ref,
    ]


def run_extension_probes(
    project_root: Path,
    pgdata_dir: Path,
    *,
    pins: ImagePins | None = None,
    password: str = "probe-secret",
    user: str = "arxiv_int",
    database: str = "arxiv_int",
) -> ProbeReport:
    """Build-time/runtime suite against a disposable PGDATA_DIR bind mount."""
    if shutil.which("docker") is None:
        report = ProbeReport()
        report.add("docker", False, "docker unavailable")
        return report
    resolved = pins or load_image_pins(project_root)
    report = ProbeReport(image_ref=resolved.local_image_ref)
    notice = project_root / "docker" / "postgres" / "NOTICE"
    check_licenses(notice.read_text(encoding="utf-8") if notice.is_file() else "", report)
    pgdata_dir.mkdir(parents=True, exist_ok=True)
    container = f"arxiv-int-ext-{os.getpid()}-{int(time.time()) % 100000}"
    common = disposable_database_run_args(
        container=container,
        image_ref=resolved.local_image_ref,
        pgdata_dir=pgdata_dir,
        password=password,
        db_user=user,
        database=database,
    )
    _LOG.info("disposable database runs as host user %s", host_user_spec())
    try:
        started = subprocess.run(
            [*common[:-1], "-d", common[-1]], check=False, capture_output=True, text=True
        )
        if started.returncode != 0:
            report.add("start", False, started.stderr.strip() or "failed to start container")
            return report
        if not wait_ready(container, user, database):
            report.add("start", False, "database did not become ready")
            return report
        report.add("start", True, "container healthy")
        probe_versions(container, user, database, password, resolved, report)
        age_ok = probe_named(container, user, database, password, "cypher", CYPHER_SQL, report)
        probe_named(container, user, database, password, "bm25_vector", BM25_VECTOR_SQL, report)
        probe_named(container, user, database, password, "transaction", TXN_SQL, report)
        probe_restart(container, common, user, database, password, report)
        probe_dump_restore(container, user, database, password, report)
        report.age_compatible = age_ok and report.all_core_passed
        if report.age_compatible:
            report.add("age_gate", True, "AGE coexistence probes passed")
        else:
            cypher = next((item for item in report.results if item.name == "cypher"), None)
            detail = cypher.detail if cypher and not cypher.ok else "core probes failed"
            report.add("age_gate", False, detail)
        return report
    finally:
        subprocess.run(
            ["docker", "rm", "-f", container], check=False, capture_output=True, text=True
        )
