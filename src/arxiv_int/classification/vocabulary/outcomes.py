"""Class-id namespaces and the two mandatory outcomes.

Taxonomy classes, operator-local extensions, and exceptional outcomes live in disjoint namespaces
so a local subdivision or an outcome can never be mistaken for a shipped taxonomy class.
"""

NAMESPACE_TAXONOMY = "tax"
NAMESPACE_EXTENSION = "ext"
NAMESPACE_OUTCOME = "outcome"
NAMESPACES = (NAMESPACE_TAXONOMY, NAMESPACE_EXTENSION, NAMESPACE_OUTCOME)

TAXONOMY_PREFIX = f"{NAMESPACE_TAXONOMY}:"
EXTENSION_PREFIX = f"{NAMESPACE_EXTENSION}:"

OUTCOME_UNCLASSIFIED = "unclassified"
OUTCOME_UNREADABLE = "unreadable"
EXCEPTIONAL_OUTCOMES = frozenset({OUTCOME_UNCLASSIFIED, OUTCOME_UNREADABLE})


def taxonomy_class_id(code: str) -> str:
    """Return the class id for one taxonomy code."""
    return f"{TAXONOMY_PREFIX}{code}"


def extension_class_id(name: str) -> str:
    """Return the class id for one operator-local extension name."""
    return f"{EXTENSION_PREFIX}{name}"


def namespace_of(class_id: str) -> str:
    """Return the namespace of a class id or raise for an unknown shape."""
    if class_id in EXCEPTIONAL_OUTCOMES:
        return NAMESPACE_OUTCOME
    if class_id.startswith(TAXONOMY_PREFIX) and len(class_id) > len(TAXONOMY_PREFIX):
        return NAMESPACE_TAXONOMY
    if class_id.startswith(EXTENSION_PREFIX) and len(class_id) > len(EXTENSION_PREFIX):
        return NAMESPACE_EXTENSION
    raise ValueError(f"class id '{class_id}' is not in the tax, ext, or outcome namespace")
