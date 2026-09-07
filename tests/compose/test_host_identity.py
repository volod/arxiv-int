"""Host identity helpers for Compose and disposable Docker runs."""

import os
from pathlib import Path

from arxiv_int.runtime.host_identity import docker_user_args, host_user_spec
from arxiv_int.stores.postgres_image.probes import disposable_database_run_args


def test_host_user_spec_matches_process_identity() -> None:
    assert host_user_spec() == f"{os.getuid()}:{os.getgid()}"
    assert docker_user_args() == ("--user", host_user_spec())


def test_disposable_database_run_uses_host_user(tmp_path: Path) -> None:
    command = disposable_database_run_args(
        container="arxiv-int-ext-test",
        image_ref="arxiv-int/postgres:test",
        pgdata_dir=tmp_path / "pgdata",
        password="secret",
        db_user="arxiv_int",
        database="arxiv_int",
    )
    assert "--user" in command
    assert command[command.index("--user") + 1] == host_user_spec()
    assert str(tmp_path / "pgdata") in " ".join(command)
