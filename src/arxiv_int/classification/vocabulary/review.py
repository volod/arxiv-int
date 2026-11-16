"""Draft human-review packet content for the classification taxonomy.

The packet is a draft contribution to ``approve-classification-operating-point``: it names the
exact scheme, taxonomy version and licence, source coverage, balance statistics, outcomes and
extensions. It carries no thresholds (the classifier task adds those) and it is never an approval.
"""

from collections.abc import Sequence
from typing import Any

from arxiv_int.classification.vocabulary.outcomes import NAMESPACE_EXTENSION, NAMESPACE_TAXONOMY

HUMAN_TASK = "approve-classification-operating-point"
DECISION = (
    "accept/revise the thresholds and exceptional outcomes, or retain unclassified; a changed "
    "taxonomy fingerprint needs a new taxonomy decision"
)


def vocabulary_packet(
    manifest: dict[str, Any], rows: Sequence[dict[str, Any]], *, inspect_command: str
) -> dict[str, Any]:
    """Return the vocabulary section of the classification review packet."""
    domains = [
        {"captionEn": row["caption_en"], "classId": row["class_id"], "code": row["code"]}
        for row in rows
        if row["namespace"] == NAMESPACE_TAXONOMY and row["parent_class_id"] is None
    ]
    return {
        "balance": manifest.get("balance"),
        "counts": manifest.get("counts"),
        "coverage": manifest.get("coverage"),
        "decision": DECISION,
        "domains": domains,
        "extensions": [row["class_id"] for row in rows if row["namespace"] == NAMESPACE_EXTENSION],
        "humanTask": HUMAN_TASK,
        "inspect": inspect_command,
        "outcomes": manifest.get("outcomes"),
        "pending": [
            "thresholds and exception examples (implement-hierarchical-file-classification)"
        ],
        "primaryKinds": manifest.get("primaryKinds"),
        "readiness": "draft",
        "schemeId": manifest.get("schemeId"),
        "schemeVersion": manifest.get("schemeVersion"),
        "sources": manifest.get("sources"),
        "taxonomy": manifest.get("taxonomy"),
    }
