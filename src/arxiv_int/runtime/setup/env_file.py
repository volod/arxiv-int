"""Create or append-sync `.env` and name required operator edits."""

from pathlib import Path

from arxiv_int.runtime.config import ConfigurationError, load_runtime_config
from arxiv_int.runtime.config_schema import selected
from arxiv_int.runtime.dotenv import read_dotenv

REQUIRED_ROOTS = ("RESULTS_DIR", "PGDATA_DIR")
PASSWORD_NAME = "POSTGRES_PASSWORD"


def sync_dotenv_file(project_root: Path) -> str:
    """Copy `.env.example` when `.env` is absent; append only missing declarations."""
    example = project_root / ".env.example"
    env_file = project_root / ".env"
    if not example.is_file():
        raise ConfigurationError(f"missing {example}")
    if not env_file.exists():
        env_file.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        return "created .env from .env.example"
    if not env_file.is_file():
        raise ConfigurationError(f"{env_file} is not a regular file")
    present = set(read_dotenv(env_file))
    present.update(_declared_names(env_file))
    appended: list[str] = []
    for line in example.read_text(encoding="utf-8").splitlines():
        name = _declared_name(line)
        if name is None or name in present:
            continue
        if not appended:
            with env_file.open("a", encoding="utf-8") as stream:
                stream.write("\n# Added from .env.example by setup.\n")
        with env_file.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")
        present.add(name)
        appended.append(name)
    if appended:
        return f"added {len(appended)} missing variable declaration(s) to .env"
    return "dotenv already complete"


def _declared_name(line: str) -> str | None:
    stripped = line.strip()
    if stripped.startswith("#"):
        stripped = stripped.lstrip("#").strip()
    if stripped.startswith("export "):
        stripped = stripped[7:].strip()
    name, separator, _value = stripped.partition("=")
    if not separator:
        return None
    token = name.strip()
    if token in selected({token: "x"}):
        return token
    return token if token.isidentifier() and token.isupper() else None


def _declared_names(path: Path) -> set[str]:
    names: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        name = _declared_name(line)
        if name is not None:
            names.add(name)
    return names


def missing_required_edits(
    project_root: Path, environment: dict[str, str] | None = None
) -> tuple[str, ...]:
    """Name operator edits required before product writes or service startup."""
    try:
        config = load_runtime_config(project_root=project_root, environment=environment)
    except ConfigurationError as error:
        detail = str(error)
        if "missing required configuration:" in detail:
            listed = detail.split(":", 1)[1]
            return tuple(item.strip() for item in listed.split(",") if item.strip())
        return (detail,)
    values = dict(config.values)
    missing: list[str] = []
    if not values.get(PASSWORD_NAME, "").strip():
        missing.append(PASSWORD_NAME)
    return tuple(missing)
