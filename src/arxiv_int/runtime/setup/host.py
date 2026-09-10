"""Host prerequisite checks that do not install OS packages."""

from collections.abc import Callable
from pathlib import Path
from subprocess import CompletedProcess

HOST_TOOLS: tuple[tuple[str, str], ...] = (
    ("uv", "install uv from https://docs.astral.sh/uv/"),
    ("python3", "install Python 3.12+"),
    ("docker", "install Docker Engine with Compose"),
)
Which = Callable[[str], str | None]
CommandRunner = Callable[..., CompletedProcess[str]]
TESSERACT_LANGUAGES = frozenset({"deu", "eng", "rus", "ukr"})
TESSERACT_INSTALL = (
    "sudo apt install tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng "
    "tesseract-ocr-deu tesseract-ocr-ukr"
)


def missing_host_tools(which: Which) -> tuple[tuple[str, str], ...]:
    """Return missing host tools and their operator actions."""
    return tuple((name, action) for name, action in HOST_TOOLS if which(name) is None)


def docker_compose_available(which: Which) -> bool:
    """Return whether the Compose plugin or docker-compose binary is present."""
    return which("docker") is not None


def missing_extraction_prerequisites(
    which: Which,
    runner: CommandRunner,
    project_root: Path,
) -> tuple[str, ...]:
    """Return missing Tesseract executable/languages for the extraction profile."""
    if which("tesseract") is None:
        return ("tesseract", *sorted(TESSERACT_LANGUAGES))
    completed = runner(("tesseract", "--list-langs"), cwd=project_root)
    if completed.returncode != 0:
        return ("tesseract", *sorted(TESSERACT_LANGUAGES))
    installed = frozenset(line.strip() for line in completed.stdout.splitlines())
    return tuple(sorted(TESSERACT_LANGUAGES - installed))
