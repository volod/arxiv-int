"""Synthetic taxonomy projects written as a ``configs/classification`` overlay.

The fixture taxonomy is two domains, each with two fields of two subfields, and one synthetic
source whose items map to the subfields. Russian and Ukrainian captions are escapes so sources
stay ASCII.
"""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from arxiv_int.resources.paths import configs_root

RU = "\u0420\u0423"
UK = "\u0423\u041a"
SOURCE_PREFIX = "fixture:item/"
MIT = {"name": "MIT", "url": "https://opensource.org/license/mit"}
CC0 = {"name": "CC0 1.0", "url": "https://creativecommons.org/publicdomain/zero/1.0/"}


def captions(text: str) -> dict[str, str]:
    """Return en/ru/uk captions for one fixture class."""
    return {"en": text, "ru": f"{RU} {text}", "uk": f"{UK} {text}"}


def fixture_classes() -> list[dict[str, Any]]:
    """Return a balanced two-by-two-by-two taxonomy with one source item per subfield."""
    classes: list[dict[str, Any]] = []
    for domain in ("01", "02"):
        classes.append({"captions": captions(f"Domain {domain}"), "code": domain})
        for field in ("01", "02"):
            field_code = f"{domain}.{field}"
            classes.append({"captions": captions(f"Field {field_code}"), "code": field_code})
            for subfield in ("01", "02"):
                code = f"{field_code}.{subfield}"
                classes.append(
                    {
                        "captions": captions(f"Subfield {code}"),
                        "code": code,
                        "crosswalk": [f"{SOURCE_PREFIX}{code}"],
                    }
                )
    return classes


def source_items(classes: Sequence[Mapping[str, Any]]) -> list[str]:
    """Return every crosswalk reference of the given classes."""
    return [ref for item in classes for ref in item.get("crosswalk", ())]


def _write(path: Path, document: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(document, indent=2, ensure_ascii=True), encoding="ascii")


def write_project(
    root: Path,
    *,
    classes: Sequence[Mapping[str, Any]] | None = None,
    items: Sequence[str] | None = None,
    extensions: Sequence[Mapping[str, Any]] = (),
    taxonomy_licence: Mapping[str, str] = MIT,
) -> Path:
    """Write a project root whose classification policy uses the fixture taxonomy."""
    chosen = list(classes if classes is not None else fixture_classes())
    configs = root / "configs" / "classification"
    (configs / "sources").mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname = 'fixture'\n", encoding="utf-8")
    policy = json.loads((configs_root() / "classification" / "scheme.json").read_text("utf-8"))
    policy["sources"] = ["sources/fixture.json"]
    policy["balance"]["maxDomainLeafShare"] = 0.5
    _write(configs / "scheme.json", policy)
    _write(
        configs / "taxonomy.json",
        {
            "classes": chosen,
            "copyright": "fixture",
            "licence": dict(taxonomy_licence),
            "taxonomyId": "fixture-subjects",
            "title": "Fixture taxonomy",
            "version": "0.1.0",
        },
    )
    references = list(items if items is not None else source_items(chosen))
    _write(
        configs / "sources" / "fixture.json",
        {
            "items": [{"id": ref, "name": ref} for ref in references],
            "licence": CC0,
            "publisher": "fixture",
            "retrievedAt": "2026-09-11",
            "sourceId": "fixture-source",
            "url": "https://fixture.invalid/items",
        },
    )
    _write(configs / "extensions.json", {"extensions": list(extensions), "extensionsVersion": "1"})
    return root
