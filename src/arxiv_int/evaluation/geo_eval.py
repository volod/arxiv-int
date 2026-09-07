"""Ontology evolution and geotemporal fixture scoring."""

from collections.abc import Mapping

from arxiv_int.evaluation.domain_eval import field_agreement


def score_ontology(
    gold: Mapping[str, object], prediction: Mapping[str, object]
) -> dict[str, float]:
    """Score add, deprecate, draft, and contradiction ontology cases."""
    action = float(gold.get("action") == prediction.get("action"))
    change = 1.0
    if "change" in gold:
        change = float(gold.get("change") == prediction.get("change"))
    allowed = 1.0
    if "allowed" in gold:
        allowed = float(bool(gold.get("allowed")) == bool(prediction.get("allowed")))
    successor = 1.0
    if "successor" in gold:
        successor = float(gold.get("successor") == prediction.get("successor"))
        if gold.get("action") == "deprecate" and not prediction.get("successor"):
            successor = 0.0
    draft_refused = 1.0
    if gold.get("action") == "draft":
        draft_refused = float(prediction.get("allowed") is False)
    contradiction_refused = 1.0
    if gold.get("action") == "contradiction":
        contradiction_refused = float(prediction.get("allowed") is False)
    return {
        "action_match": action,
        "allowed_match": allowed,
        "change_match": change,
        "contradiction_refused": contradiction_refused,
        "draft_refused": draft_refused,
        "successor_match": successor,
    }


def score_geotemporal(
    gold: Mapping[str, object], prediction: Mapping[str, object]
) -> dict[str, float]:
    """Keep source-valid time, CRS uncertainty, and effectivity distinct."""
    time_fields = (
        "source_valid_start",
        "source_valid_end",
        "recorded_time",
        "role_start",
        "role_end",
        "as_of",
        "revision",
        "revision_a_end",
        "revision_b_start",
    )
    present = tuple(name for name in time_fields if name in gold)
    time_agreement = field_agreement(gold, prediction, present)
    source = gold.get("source_valid_start")
    recorded = gold.get("recorded_time")
    distinct = 1.0
    if source is not None and recorded is not None:
        distinct = float(prediction.get("source_valid_start") != prediction.get("recorded_time"))
    unknown = float(bool(gold.get("unknown_crs")) == bool(prediction.get("unknown_crs")))
    if gold.get("unknown_crs") and prediction.get("crs") not in {None, ""}:
        unknown = 0.0
    role = 1.0
    if "role_active" in gold:
        role = float(bool(gold.get("role_active")) == bool(prediction.get("role_active")))
    coords_ok = 1.0
    if gold.get("latitude") is not None:
        coords_ok = field_agreement(gold, prediction, ("latitude", "longitude", "crs"))
    return {
        "coordinates_kept": coords_ok,
        "role_interval_match": role,
        "source_recorded_distinct": distinct,
        "time_agreement": time_agreement,
        "unknown_crs_kept": unknown,
    }
