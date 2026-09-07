"""Documented normalization for versioned proof-identity hashing."""

import unicodedata


def normalize_identity(text: str) -> str:
    """Apply NFKC and strip surrounding whitespace."""
    return unicodedata.normalize("NFKC", text).strip()


def collapse_space(text: str) -> str:
    """Collapse internal whitespace after identity normalization."""
    return " ".join(normalize_identity(text).split())


def normalize_email(text: str) -> str:
    """Lowercase a normalized email address."""
    return collapse_space(text).lower()


def normalize_phone(text: str) -> str:
    """Keep an optional leading plus and decimal digits only."""
    stripped = normalize_identity(text)
    prefix = "+" if stripped.startswith("+") else ""
    digits = "".join(char for char in stripped if char.isdigit())
    return f"{prefix}{digits}"


def normalize_account(text: str) -> str:
    """Uppercase an account value and drop spaces."""
    return collapse_space(text).replace(" ", "").upper()


def digit_string(text: str) -> str:
    """Return decimal digits from a formatted identity value."""
    return "".join(char for char in text if char.isdigit())
