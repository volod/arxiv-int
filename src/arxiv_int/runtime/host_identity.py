"""Host identity used for Compose and disposable Docker bind mounts."""

import os


def host_uid() -> int:
    """Return the invoking process user id."""
    return os.getuid()


def host_gid() -> int:
    """Return the invoking process group id."""
    return os.getgid()


def host_user_spec() -> str:
    """Return ``uid:gid`` for Compose ``user:`` and ``docker run --user``."""
    return f"{host_uid()}:{host_gid()}"


def docker_user_args() -> tuple[str, ...]:
    """Return Docker CLI args so bind-mounted artifacts stay host-owned."""
    return ("--user", host_user_spec())
