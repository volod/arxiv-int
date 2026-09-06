"""Stable application hash bucket used beside PostgreSQL HASH(pk) partitions."""

import hashlib

from arxiv_int.stores.postgres.constants import HASH_MODULUS

# First seven hex digits of SHA-256 stay inside a signed 28-bit integer so the
# SQL function ctl.partition_bucket can use bit(28)::int without sign wrapping.
_HEX_CHARS = 7


def partition_bucket(key: str, modulus: int = HASH_MODULUS) -> str:
    """Return the decimal remainder used as the application ``bucket`` value."""
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return str(int(digest[:_HEX_CHARS], 16) % modulus)


def partition_bucket_sql(modulus: int = HASH_MODULUS) -> str:
    """Return the frozen SQL body that must stay equivalent to ``partition_bucket``."""
    return (
        "SELECT (("
        f"('x' || left(encode(sha256(convert_to(key, 'UTF8')), 'hex'), {_HEX_CHARS}))"
        f"::bit({_HEX_CHARS * 4})::int) % {modulus})::text"
    )
