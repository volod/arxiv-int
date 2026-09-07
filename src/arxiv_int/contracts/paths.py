"""Rooted file-reference validation for contract trees."""

import pathlib

_NULL = "\x00"


def resolve_rooted_reference(
    root: pathlib.Path,
    reference: str,
    *,
    label: str = "Contract reference",
) -> pathlib.Path:
    """Resolve a relative reference that must remain under ``root`` after symlinks.

    Absolute references, empty values, null bytes, parent traversal, and symlink
    targets outside the resolved root are refused.
    """
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError(f"{label} is empty")
    if _NULL in reference:
        raise ValueError(f"{label} contains a null byte: {reference!r}")
    candidate = pathlib.Path(reference)
    if candidate.is_absolute():
        raise ValueError(f"{label} must be relative to the contract root: {reference}")
    resolved_root = root.expanduser().resolve()
    resolved = (resolved_root / candidate).resolve()
    if not resolved.is_relative_to(resolved_root):
        raise ValueError(f"{label} escapes contract root: {reference}")
    return resolved
