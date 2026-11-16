"""Load the committed classification policy, subject taxonomy, source snapshots and extensions."""

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from arxiv_int.classification.vocabulary.model import caption_pairs
from arxiv_int.resources.paths import configs_root

POLICY_DIRNAME = "classification"
SCHEME_POLICY_FILE = "scheme.json"
EXTENSIONS_FILE = "extensions.json"


class PolicyError(ValueError):
    """Raised for a malformed policy, taxonomy, source snapshot or extension file."""


@dataclass(frozen=True, slots=True)
class Licence:
    """Licence name and reference URL."""

    name: str
    url: str


@dataclass(frozen=True, slots=True)
class BalancePolicy:
    """Structural balance limits for the shipped taxonomy."""

    leaf_depth: int
    min_children: int
    max_children: int
    max_domain_leaf_share: float


@dataclass(frozen=True, slots=True)
class TaxonomyEntry:
    """One taxonomy class as authored: code, captions and source crosswalk ids."""

    code: str
    captions: tuple[tuple[str, str], ...]
    crosswalk: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Taxonomy:
    """The project-authored subject taxonomy and its file fingerprint."""

    taxonomy_id: str
    title: str
    version: str
    licence: Licence
    copyright: str
    entries: tuple[TaxonomyEntry, ...]
    sha256: str


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    """One checksummed, permissively licensed source whose items the taxonomy must cover."""

    source_id: str
    publisher: str
    licence: Licence
    url: str
    retrieved_at: str
    items: tuple[str, ...]
    sha256: str


@dataclass(frozen=True, slots=True)
class Extension:
    """One operator-local subdivision with an explicit parent link."""

    class_id: str
    parent_id: str
    captions: tuple[tuple[str, str], ...]
    rationale: str


@dataclass(frozen=True)
class SchemePolicy:
    """Committed scheme policy with its taxonomy, sources, extensions and fingerprints."""

    policy_version: str
    caption_languages: tuple[str, ...]
    required_caption_languages: tuple[str, ...]
    max_token_bytes: int
    max_slug_bytes: int
    outcomes: Mapping[str, str]
    primary_kinds: frozenset[str]
    balance: BalancePolicy
    evaluation_seed: int
    split_fractions: tuple[tuple[str, float], ...]
    taxonomy: Taxonomy
    sources: tuple[SourceSnapshot, ...]
    extensions_version: str
    extensions: tuple[Extension, ...]
    policy_sha256: str
    extensions_sha256: str

    @property
    def sources_sha256(self) -> tuple[str, ...]:
        """Return source snapshot fingerprints in policy order."""
        return tuple(source.sha256 for source in self.sources)


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PolicyError(f"{label} must be a JSON object")
    return value


def _text(document: Mapping[str, Any], key: str, label: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        raise PolicyError(f"{label}.{key} must be a non-empty string")
    return value


def _licence(document: Any, label: str) -> Licence:
    licence = _object(document, f"{label}.licence")
    return Licence(str(licence.get("name") or ""), str(licence.get("url") or ""))


def _load(directory: Path, reference: str) -> tuple[dict[str, Any], str]:
    path = (directory / reference).resolve()
    if not path.is_relative_to(directory.resolve()):
        raise PolicyError(f"{reference} escapes the classification policy directory")
    payload = path.read_bytes()
    return _object(json.loads(payload), reference), hashlib.sha256(payload).hexdigest()


def _captions(document: Any, label: str) -> tuple[tuple[str, str], ...]:
    captions = _object(document, f"{label}.captions")
    return caption_pairs({str(key): str(value) for key, value in captions.items()})


def _taxonomy(directory: Path, reference: str) -> Taxonomy:
    document, sha256 = _load(directory, reference)
    entries = tuple(
        TaxonomyEntry(
            code=_text(item, "code", "taxonomy class"),
            captions=_captions(item.get("captions"), "taxonomy class"),
            crosswalk=tuple(str(ref) for ref in item.get("crosswalk") or ()),
        )
        for item in (_object(entry, "taxonomy class") for entry in document.get("classes") or ())
    )
    return Taxonomy(
        taxonomy_id=_text(document, "taxonomyId", reference),
        title=_text(document, "title", reference),
        version=_text(document, "version", reference),
        licence=_licence(document.get("licence"), reference),
        copyright=str(document.get("copyright") or ""),
        entries=entries,
        sha256=sha256,
    )


def _source(directory: Path, reference: str) -> SourceSnapshot:
    document, sha256 = _load(directory, reference)
    return SourceSnapshot(
        source_id=_text(document, "sourceId", reference),
        publisher=_text(document, "publisher", reference),
        licence=_licence(document.get("licence"), reference),
        url=_text(document, "url", reference),
        retrieved_at=_text(document, "retrievedAt", reference),
        items=tuple(_text(_object(item, "item"), "id", reference) for item in document["items"]),
        sha256=sha256,
    )


def _extension(document: Any) -> Extension:
    item = _object(document, "extension")
    return Extension(
        class_id=_text(item, "id", "extension"),
        parent_id=_text(item, "parent", "extension"),
        captions=_captions(item.get("captions"), "extension"),
        rationale=str(item.get("rationale") or ""),
    )


def _splits(document: Mapping[str, Any]) -> tuple[tuple[str, float], ...]:
    splits = tuple(sorted((str(key), float(value)) for key, value in document.items()))
    if not splits or any(value <= 0 for _, value in splits):
        raise PolicyError("evaluation.splits must declare positive fractions")
    if abs(sum(value for _, value in splits) - 1.0) > 1e-9:
        raise PolicyError("evaluation.splits fractions must sum to 1")
    return splits


def _balance(document: Mapping[str, Any]) -> BalancePolicy:
    return BalancePolicy(
        leaf_depth=int(document["leafDepth"]),
        min_children=int(document["minChildren"]),
        max_children=int(document["maxChildren"]),
        max_domain_leaf_share=float(document["maxDomainLeafShare"]),
    )


def load_scheme_policy(project_root: Path | None = None) -> SchemePolicy:
    """Load ``configs/classification/`` policy, taxonomy, sources and extensions."""
    directory = configs_root(project_root) / POLICY_DIRNAME
    scheme, scheme_sha = _load(directory, SCHEME_POLICY_FILE)
    extensions, extensions_sha = _load(directory, EXTENSIONS_FILE)
    tokens = _object(scheme.get("tokens"), "tokens")
    evaluation = _object(scheme.get("evaluation"), "evaluation")
    outcomes = _object(scheme.get("outcomes"), "outcomes")
    return SchemePolicy(
        policy_version=_text(scheme, "policyVersion", "scheme"),
        caption_languages=tuple(str(code) for code in scheme.get("captionLanguages") or ()),
        required_caption_languages=tuple(
            str(code) for code in scheme.get("requiredCaptionLanguages") or ()
        ),
        max_token_bytes=int(tokens["maxTokenBytes"]),
        max_slug_bytes=int(tokens["maxSlugBytes"]),
        outcomes=MappingProxyType({str(key): str(value) for key, value in outcomes.items()}),
        primary_kinds=frozenset(str(kind) for kind in scheme.get("primaryKinds") or ()),
        balance=_balance(_object(scheme.get("balance"), "balance")),
        evaluation_seed=int(evaluation["seed"]),
        split_fractions=_splits(_object(evaluation.get("splits"), "evaluation.splits")),
        taxonomy=_taxonomy(directory, _text(scheme, "taxonomy", "scheme")),
        sources=tuple(_source(directory, str(ref)) for ref in scheme.get("sources") or ()),
        extensions_version=_text(extensions, "extensionsVersion", "extensions"),
        extensions=tuple(_extension(item) for item in extensions.get("extensions") or ()),
        policy_sha256=scheme_sha,
        extensions_sha256=extensions_sha,
    )
