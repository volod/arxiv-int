"""Validate inventory member addresses without treating their JSON as a filesystem path."""

import json
from typing import Any

from arxiv_int.interfaces.tokens import require_relative_path


def validate_member_address(value: str, *, quarantined: bool) -> None:
    """Accept legacy relative names or the inventory's lossless nested address chain.

    Quarantined inventory rows retain unsafe names and policy sentinels as provenance only.
    These addresses are never opened as filesystem paths by the evidence resolver.
    """
    if not value.startswith("["):
        require_relative_path(value, "member_path")
        return
    try:
        chain = json.loads(value)
        if not isinstance(chain, list) or not chain:
            raise ValueError("empty or non-list chain")
        for index, token in enumerate(chain):
            if token == "!policy" and quarantined and index == len(chain) - 1:
                continue
            if not isinstance(token, str):
                raise ValueError("member token must be a JSON string")
            _validate_position(json.loads(token), quarantined=quarantined)
    except (TypeError, ValueError) as error:
        raise ValueError("member_path has an invalid inventory address chain") from error


def _validate_position(value: Any, *, quarantined: bool) -> None:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or type(value[0]) is not int
        or value[0] < 0
        or not isinstance(value[1], str)
        or not value[1]
        or "\x00" in value[1]
    ):
        raise ValueError("member address must contain a nonnegative position and name")
    if not quarantined:
        require_relative_path(value[1], "member name")
