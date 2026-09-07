"""Host prerequisite checks that do not install OS packages."""

from collections.abc import Callable

HOST_TOOLS: tuple[tuple[str, str], ...] = (
    ("uv", "install uv from https://docs.astral.sh/uv/"),
    ("python3", "install Python 3.12+"),
    ("docker", "install Docker Engine with Compose"),
)
Which = Callable[[str], str | None]


def missing_host_tools(which: Which) -> tuple[tuple[str, str], ...]:
    """Return missing host tools and their operator actions."""
    return tuple((name, action) for name, action in HOST_TOOLS if which(name) is None)


def docker_compose_available(which: Which) -> bool:
    """Return whether the Compose plugin or docker-compose binary is present."""
    return which("docker") is not None
