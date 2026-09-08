"""BOM/financial arithmetic, catalog parity, graph/SQL parity, and domain artifacts."""

from collections.abc import Mapping, Sequence

from arxiv_int.evaluation.scoring.metrics import extraction_metrics
from arxiv_int.evaluation.scoring.payload import as_string_rows, as_strings


def _close(left: object, right: object, *, tol: float = 1e-9) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right)) <= tol
    return left == right


def field_agreement(
    gold: Mapping[str, object], prediction: Mapping[str, object], fields: Sequence[str]
) -> float:
    """Return the fraction of named fields that match."""
    if not fields:
        return 0.0
    matched = sum(_close(gold.get(name), prediction.get(name)) for name in fields)
    return matched / len(fields)


def score_arithmetic(
    gold: Mapping[str, object], prediction: Mapping[str, object]
) -> dict[str, float]:
    """Score quantity, unit, total, and allocation arithmetic."""
    fields = ("quantity", "total", "unit", "amount", "allocated", "currency")
    present = tuple(name for name in fields if name in gold)
    agreement = field_agreement(gold, prediction, present)
    overflow = 0.0
    gold_amount = gold.get("amount")
    pred_allocated = prediction.get("allocated")
    if isinstance(gold_amount, (int, float)) and isinstance(pred_allocated, (int, float)):
        overflow = float(pred_allocated <= gold_amount)
    elif "allocated" not in gold:
        overflow = 1.0
    return {"arithmetic_agreement": agreement, "allocation_within_amount": overflow}


def score_catalog(gold: Mapping[str, object], prediction: Mapping[str, object]) -> dict[str, float]:
    """Score catalog identity, labels, aliases, and removal status."""
    identity = float(gold.get("entity_id") == prediction.get("entity_id"))
    label = float(gold.get("label") == prediction.get("label"))
    status = float(gold.get("status") == prediction.get("status")) if "status" in gold else 1.0
    gold_aliases = as_strings(gold.get("aliases"))
    pred_aliases = as_strings(prediction.get("aliases"))
    aliases = (
        extraction_metrics(pred_aliases, gold_aliases).f1 if gold_aliases or pred_aliases else 1.0
    )
    distinct = float(
        gold.get("entity_id") == prediction.get("entity_id")
        or gold.get("label") != prediction.get("label")
    )
    return {
        "alias_f1": aliases,
        "identity_match": identity,
        "label_match": label,
        "same_name_distinct": distinct,
        "status_match": status,
    }


def score_graph(gold: Mapping[str, object], prediction: Mapping[str, object]) -> dict[str, float]:
    """Require predicted graph paths to equal the relational SQL rows."""
    gold_sql = as_string_rows(gold.get("sql_rows"))
    pred_path = as_strings(prediction.get("path"))
    pred_sql = as_string_rows(prediction.get("sql_rows")) or gold_sql
    path_ok = float(
        list(pred_path) in [list(row) for row in gold_sql]
        or pred_path == as_strings(gold.get("path"))
    )
    sql_ok = float(pred_sql == gold_sql)
    parity = float(path_ok == 1.0 and sql_ok == 1.0)
    return {"graph_sql_parity": parity, "path_match": path_ok, "sql_match": sql_ok}


def score_domain_artifact(
    gold: Mapping[str, object], prediction: Mapping[str, object]
) -> dict[str, float]:
    """Score BOM/invoice artifacts and valid-empty registry rows."""
    arithmetic = score_arithmetic(gold, prediction)
    status = 1.0
    if "creation_status" in gold:
        status = float(gold.get("creation_status") == prediction.get("creation_status"))
        empty_ok = 1.0
        if gold.get("creation_status") == "empty":
            empty_ok = float(prediction.get("failure_reason") in {None, ""})
        arithmetic = {**arithmetic, "registry_status": status, "valid_empty": empty_ok}
    return arithmetic


def score_domain_negative(
    gold: Mapping[str, object], prediction: Mapping[str, object]
) -> dict[str, float]:
    """Score cases that must not become valid through a related identity."""
    valid_match = float(bool(gold.get("valid")) == bool(prediction.get("valid")))
    implication = float(gold.get("implication") == prediction.get("implication"))
    refused = float(prediction.get("valid") is False)
    return {
        "implication_match": implication,
        "negative_held": refused if gold.get("valid") is False else valid_match,
        "valid_match": valid_match,
    }
