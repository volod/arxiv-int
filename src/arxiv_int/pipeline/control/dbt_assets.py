"""Selected contract source definitions from the generated dbt input actually assembled."""

from pathlib import Path
from typing import Any

from arxiv_int.contracts.catalog._yaml import load_mapping
from arxiv_int.contracts.catalog.paths import resolve_rooted_reference
from arxiv_int.pipeline.control.asset_hashes import file_hashes


def generated_dbt_inputs(root: Path, contracts: tuple[str, ...]) -> dict[str, Any]:
    """Bind per-contract definitions and their tables in the combined dbt sources file."""
    references = [f"generated/dbt/{name}.yml" for name in sorted(set(contracts))]
    if not references:
        return {}
    requested: set[tuple[str, str]] = set()
    for reference in references:
        requested.update(_tables(load_mapping(resolve_rooted_reference(root, reference))))
    combined = _tables(load_mapping(resolve_rooted_reference(root, "generated/dbt/sources.yml")))
    missing = requested - combined.keys()
    if missing:
        raise ValueError("declared contract source is missing from generated dbt sources")
    return {
        "files": file_hashes(root, references),
        "generated/dbt/sources.yml": {
            f"{source}.{table}": combined[(source, table)] for source, table in sorted(requested)
        },
    }


def _tables(document: dict[str, Any]) -> dict[tuple[str, str], Any]:
    tables: dict[tuple[str, str], Any] = {}
    for source in document.get("sources", ()):
        metadata = {key: value for key, value in source.items() if key != "tables"}
        for table in source.get("tables", ()):
            key = (str(source["name"]), str(table["name"]))
            if key in tables:
                raise ValueError("duplicate generated dbt source table")
            tables[key] = {"source": metadata, "table": table}
    return tables
