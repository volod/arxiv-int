"""Order-independent bounded metadata identity for inventory source-set drift checks."""

import hashlib
import json

from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.pipeline.inventory.walk import walk

INVENTORY_METADATA_POLICY = "inventory-stat-v1"
_MODULUS = 1 << 256


def inventory_snapshot(silos: tuple[SiloRoot, ...]) -> str:
    """Hash a counted multiset of entry metadata without retaining directory entries.

    This is a source-set change detector, never content identity. Content SHA-256 belongs
    to inventory rows. Two independent modular digest sums retain duplicate multiplicity.
    """
    count = 0
    first = second = 0
    for silo in silos:
        for entry in walk(silo.root):
            payload = json.dumps(
                [silo.silo_id, entry.relative_path, entry.status, entry.signature],
                ensure_ascii=True,
            ).encode("ascii")
            digest = hashlib.sha512(payload).digest()
            first = (first + int.from_bytes(digest[:32])) % _MODULUS
            second = (second + int.from_bytes(digest[32:])) % _MODULUS
            count += 1
    scope = json.dumps([silo.silo_id for silo in silos], ensure_ascii=True)
    return hashlib.sha256(f"{scope}:{count}:{first}:{second}".encode("ascii")).hexdigest()
