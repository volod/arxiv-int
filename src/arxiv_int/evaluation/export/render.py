"""Format-preserving substitutes for entities, contacts, addresses, and accounts."""

from arxiv_int.evaluation.export.catalog import CatalogEntity, CatalogField
from arxiv_int.evaluation.export.errors import ExportError
from arxiv_int.evaluation.export.normalize import (
    digit_string,
    normalize_account,
    normalize_email,
    normalize_identity,
    normalize_phone,
)
from arxiv_int.evaluation.export.policy import EMAIL_DOMAIN, namespaced_digest

INN10_WEIGHTS = (2, 4, 10, 3, 5, 9, 4, 6, 8)
INN12_WEIGHTS_11 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
INN12_WEIGHTS_12 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
IBAN_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


class ExportRenderError(ExportError):
    """A typed field cannot be rendered in its required shape."""


def entity_label(entity: CatalogEntity) -> str:
    """Return `{kind}_{digest}` from the stable entity id."""
    digest = namespaced_digest(f"entity.{entity.kind}", normalize_identity(entity.entity_id))
    return f"{entity.kind}_{digest}"


def email_substitute(value: str) -> str:
    """Return a `.invalid` contact address from the normalized email."""
    digest = namespaced_digest("field.email", normalize_email(value))
    return f"contact_{digest}@{EMAIL_DOMAIN}"


def phone_substitute(field: CatalogField) -> str:
    """Preserve punctuation and prefix; replace remaining digits from the hash."""
    original = field.value
    normalized = normalize_phone(original)
    digest = namespaced_digest("field.phone", normalized)
    digits = digit_string(original)
    if not digits:
        raise ExportRenderError("phone value has no digits")
    prefix_digits = digit_string(field.prefix)
    if prefix_digits and not digits.startswith(prefix_digits):
        raise ExportRenderError("phone prefix is not present in the value")
    kept = len(prefix_digits)
    generated = _decimal_digits(digest, len(digits) - kept, allow_leading_zero=False)
    replacement = digits[:kept] + generated
    return _apply_digit_mask(original, replacement)


def account_substitute(field: CatalogField) -> str:
    """Return a same-shape account with replacement check digits when required."""
    original = field.value
    normalized = normalize_account(original)
    digest = namespaced_digest(f"field.account.{field.scheme}", normalized)
    if field.scheme == "iban":
        return _iban_substitute(normalized, digest)
    digits = digit_string(original)
    if field.scheme == "luhn":
        body = _decimal_digits(digest, len(digits) - 1, allow_leading_zero=False)
        rendered = body + luhn_check_digit(body)
        return _apply_digit_mask(original, rendered)
    if field.scheme == "inn10":
        body = _decimal_digits(digest, 9, allow_leading_zero=True)
        rendered = body + inn10_check_digit(body)
        return _apply_digit_mask(original, rendered)
    if field.scheme == "inn12":
        body = _decimal_digits(digest, 10, allow_leading_zero=True)
        first = inn12_check_digits(body)
        rendered = body + first
        return _apply_digit_mask(original, rendered)
    rendered = _decimal_digits(digest, len(digits), allow_leading_zero=True)
    return _apply_digit_mask(original, rendered)


def address_substitutes(field: CatalogField) -> dict[str, str]:
    """Return synthetic street/city labels and numeric house/postal fields."""
    mapping: dict[str, str] = {}
    if field.street:
        digest = namespaced_digest("field.address.street", normalize_identity(field.street))
        mapping[field.street] = f"Street_{digest[:12]}"
    if field.city:
        digest = namespaced_digest("field.address.city", normalize_identity(field.city))
        mapping[field.city] = f"City_{digest[:12]}"
    if field.country and len(field.country) >= 3:
        digest = namespaced_digest("field.address.country", normalize_identity(field.country))
        mapping[field.country] = f"Country_{digest[:12]}"
    if field.house:
        digest = namespaced_digest("field.address.house", normalize_identity(field.house))
        mapping[field.house] = _decimal_digits(
            digest, len(digit_string(field.house) or field.house), True
        )
    if field.postal:
        digest = namespaced_digest("field.address.postal", normalize_identity(field.postal))
        mapping[field.postal] = _decimal_digits(
            digest, len(digit_string(field.postal) or field.postal), True
        )
    street = mapping.get(field.street, field.street)
    house = mapping.get(field.house, field.house)
    city = mapping.get(field.city, field.city)
    postal = mapping.get(field.postal, field.postal)
    country = mapping.get(field.country, field.country)
    mapping[field.value] = _address_value(street, house, city, postal, country)
    return mapping


def luhn_check_digit(body: str) -> str:
    """Return the Luhn check digit for ``body`` without the check digit."""
    total = 0
    for index, char in enumerate(reversed(body), start=1):
        digit = int(char)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return str((10 - (total % 10)) % 10)


def luhn_valid(number: str) -> bool:
    """Return True when ``number`` including its check digit is Luhn-valid."""
    digits = digit_string(number)
    return bool(digits) and luhn_check_digit(digits[:-1]) == digits[-1]


def inn10_check_digit(body: str) -> str:
    """Return the tenth INN check digit."""
    total = sum(int(body[index]) * weight for index, weight in enumerate(INN10_WEIGHTS))
    return str((total % 11) % 10)


def inn12_check_digits(body: str) -> str:
    """Return the two trailing INN-12 check digits for a 10-digit body."""
    first = _inn_digit(body, INN12_WEIGHTS_11)
    second = _inn_digit(body + first, INN12_WEIGHTS_12)
    return first + second


def iban_check_digits(country: str, bban: str) -> str:
    """Return IBAN check digits so country+check+bban is mod-97 valid."""
    remainder = _iban_mod97(bban + country + "00")
    return f"{98 - remainder:02d}"


def iban_valid(value: str) -> bool:
    """Return True when an IBAN compact form has a valid mod-97 checksum."""
    compact = normalize_account(value)
    return len(compact) >= 5 and _iban_mod97(compact[4:] + compact[:4]) == 1


def _inn_digit(body: str, weights: tuple[int, ...]) -> str:
    total = sum(int(body[index]) * weight for index, weight in enumerate(weights))
    return str((total % 11) % 10)


def _iban_substitute(compact: str, digest: str) -> str:
    if len(compact) < 5 or not compact[:2].isalpha() or not compact[2:4].isdigit():
        raise ExportRenderError("IBAN value is malformed")
    country = compact[:2]
    bban = _alphabet_from_digest(digest, len(compact) - 4)
    return country + iban_check_digits(country, bban) + bban


def _iban_mod97(rearranged: str) -> int:
    remainder = 0
    for char in rearranged:
        chunk = str(ord(char) - 55) if char.isalpha() else char
        for digit in chunk:
            remainder = (remainder * 10 + int(digit)) % 97
    return remainder


def _decimal_digits(digest: str, length: int, allow_leading_zero: bool) -> str:
    if length <= 0:
        raise ExportRenderError("digit length must be positive")
    raw = format(int(digest, 16), "d")
    if len(raw) < length:
        raw = raw.zfill(length)
    digits = raw[-length:]
    if not allow_leading_zero and length > 1 and digits.startswith("0"):
        digits = "1" + digits[1:]
    return digits


def _alphabet_from_digest(digest: str, length: int) -> str:
    number = int(digest, 16)
    chars: list[str] = []
    for _ in range(length):
        number, remainder = divmod(number, len(IBAN_ALPHABET))
        chars.append(IBAN_ALPHABET[remainder])
    return "".join(chars)


def _apply_digit_mask(original: str, digits: str) -> str:
    chars: list[str] = []
    index = 0
    for char in original:
        if char.isdigit():
            chars.append(digits[index])
            index += 1
        else:
            chars.append(char)
    if index != len(digits):
        raise ExportRenderError("digit mask length mismatch")
    return "".join(chars)


def _address_value(street: str, house: str, city: str, postal: str, country: str) -> str:
    parts = [part for part in (f"{street} {house}".strip(), city, postal, country) if part]
    return ", ".join(parts)
