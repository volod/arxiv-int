"""Immutable scheme classes, parent closure, and nearest-ancestor resolution."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from arxiv_int.classification.vocabulary.codes import CODE_PATTERN, parent_code
from arxiv_int.classification.vocabulary.outcomes import taxonomy_class_id

ANCESTOR_SEPARATOR = ">"


class SchemeCycleError(ValueError):
    """Raised when parent links loop instead of reaching a root."""


@dataclass(frozen=True, slots=True)
class SchemeClass:
    """One class before derived fields: identity, parent link, kind, captions, crosswalk."""

    class_id: str
    namespace: str
    code: str | None
    parent_id: str | None
    kind: str
    captions: tuple[tuple[str, str], ...]
    crosswalk: tuple[str, ...] = ()

    def caption(self, language: str) -> str | None:
        """Return the caption in one language, if present."""
        for code, text in self.captions:
            if code == language:
                return text
        return None


@dataclass(frozen=True, slots=True)
class Resolution:
    """Nearest scheme class for a requested code and whether it was truncated."""

    class_id: str
    requested: str
    truncated: bool


def caption_pairs(captions: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
    """Return non-empty captions as sorted, immutable language/text pairs."""
    return tuple(sorted((code, text) for code, text in captions.items() if text))


@dataclass(frozen=True)
class Scheme:
    """An ordered class catalogue with parent closure over explicit parent links."""

    classes: Mapping[str, SchemeClass]
    _ancestors: dict[str, tuple[str, ...]] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "classes", MappingProxyType(dict(self.classes)))

    @classmethod
    def of(cls, items: Iterable[SchemeClass]) -> "Scheme":
        """Build a scheme; duplicates are rejected by validation, not silently kept."""
        return cls({item.class_id: item for item in items})

    def ancestors(self, class_id: str) -> tuple[str, ...]:
        """Return root-first ancestors of a class (excluding itself)."""
        cached = self._ancestors.get(class_id)
        if cached is not None:
            return cached
        chain: list[str] = []
        seen = {class_id}
        parent = self.classes[class_id].parent_id
        while parent is not None:
            if parent in seen:
                raise SchemeCycleError(f"parent links of {class_id} loop through {parent}")
            if parent not in self.classes:
                raise KeyError(f"{class_id} has missing ancestor {parent}")
            seen.add(parent)
            chain.append(parent)
            parent = self.classes[parent].parent_id
        result = tuple(reversed(chain))
        self._ancestors[class_id] = result
        return result

    def path(self, class_id: str) -> tuple[str, ...]:
        """Return the root-first path ending with the class itself."""
        return (*self.ancestors(class_id), class_id)

    def depth(self, class_id: str) -> int:
        """Return 1 for a root class and one more per ancestor."""
        return len(self.ancestors(class_id)) + 1

    def children(self, class_id: str | None) -> tuple[str, ...]:
        """Return direct children in catalogue order (roots for ``None``)."""
        return tuple(item.class_id for item in self.classes.values() if item.parent_id == class_id)

    def resolve_code(self, code: str) -> Resolution | None:
        """Resolve a code to itself or its nearest present ancestor.

        A code deeper than the taxonomy resolves to the closest shipped class with
        ``truncated=True``; no deeper class is invented. ``None`` means not even the domain exists.
        """
        if CODE_PATTERN.fullmatch(code) is None:
            return None
        candidate: str | None = code
        truncated = False
        while candidate is not None:
            class_id = taxonomy_class_id(candidate)
            if class_id in self.classes:
                return Resolution(class_id, code, truncated)
            candidate = parent_code(candidate)
            truncated = True
        return None
