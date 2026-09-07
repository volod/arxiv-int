"""Load pinned identities for the project-owned PostgreSQL image."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ImagePins:
    """Exact upstream and project image identities."""

    paradedb_image: str
    paradedb_digest: str
    postgres_major: str
    postgres_version: str
    pg_search_version: str
    vector_version: str
    age_git_sha: str
    age_version: str
    image_name: str
    image_tag: str

    @property
    def base_image_ref(self) -> str:
        return f"{self.paradedb_image}@{self.paradedb_digest}"

    @property
    def local_image_ref(self) -> str:
        return f"{self.image_name}:{self.image_tag}"

    def expected_extensions(self) -> dict[str, str]:
        return {
            "vector": self.vector_version,
            "pg_search": self.pg_search_version,
            "age": self.age_version,
        }


def postgres_dir(project_root: Path) -> Path:
    """Return the repository docker/postgres directory."""
    return project_root / "docker" / "postgres"


def load_image_pins(project_root: Path) -> ImagePins:
    """Parse docker/postgres/pins.env into typed pins."""
    path = postgres_dir(project_root) / "pins.env"
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip()
    required = (
        "PARADEDB_IMAGE",
        "PARADEDB_DIGEST",
        "POSTGRES_MAJOR",
        "POSTGRES_VERSION",
        "PG_SEARCH_VERSION",
        "VECTOR_VERSION",
        "AGE_GIT_SHA",
        "AGE_VERSION",
        "IMAGE_NAME",
        "IMAGE_TAG",
    )
    missing = [name for name in required if name not in values]
    if missing:
        raise ValueError(f"pins.env missing keys: {', '.join(missing)}")
    return ImagePins(
        paradedb_image=values["PARADEDB_IMAGE"],
        paradedb_digest=values["PARADEDB_DIGEST"],
        postgres_major=values["POSTGRES_MAJOR"],
        postgres_version=values["POSTGRES_VERSION"],
        pg_search_version=values["PG_SEARCH_VERSION"],
        vector_version=values["VECTOR_VERSION"],
        age_git_sha=values["AGE_GIT_SHA"],
        age_version=values["AGE_VERSION"],
        image_name=values["IMAGE_NAME"],
        image_tag=values["IMAGE_TAG"],
    )


def merge_shared_preload(current: str, library: str) -> str:
    """Append a preload library without dropping existing entries."""
    libs = [item.strip() for item in current.split(",") if item.strip()]
    if library not in libs:
        libs.append(library)
    return ",".join(libs)
