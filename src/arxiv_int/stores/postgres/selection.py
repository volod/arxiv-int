"""Select the canonical store URL for load, projection, and retrieval commands."""

from pathlib import Path

from arxiv_int.contracts.migrations.runner import resolve_database_url


class StoreUnavailableError(RuntimeError):
    """Raised when no canonical store is selected or configured."""


def store_database_url(project_root: Path) -> str:
    """Return the selected store URL, or the configured loopback service URL."""
    explicit = resolve_database_url()
    if explicit:
        return explicit
    from arxiv_int.runtime import ConfigurationError
    from arxiv_int.runtime.config import load_runtime_config
    from arxiv_int.runtime.setup.schema import service_database_url

    try:
        return service_database_url(load_runtime_config(project_root=project_root))
    except (ConfigurationError, OSError, ValueError) as error:
        raise StoreUnavailableError(
            "no canonical store selected; run 'make setup-schema' or set "
            f"ARXIV_INT_MIGRATION_DATABASE_URL ({error})"
        ) from error
