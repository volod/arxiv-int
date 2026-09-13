"""Terminal prompts for an explicit human archive gold label."""

from typing import Any, TextIO

from arxiv_int.classification.labels import resolve_label
from arxiv_int.classification.review_material import evidence_terms, review_preview


def say(output: TextIO, message: str = "") -> None:
    output.write(message + "\n")
    output.flush()


def ask(input_stream: TextIO, output: TextIO, prompt: str) -> str:
    output.write(prompt)
    output.flush()
    answer = input_stream.readline()
    if not answer:
        raise ValueError("review stopped at end of input; confirmed labels were retained")
    return answer.strip()


def _show_class(scheme: Any, target: str, output: TextIO) -> None:
    resolved = scheme.resolve_code(target)
    identity = resolved.class_id if resolved is not None else target
    item = scheme.classes.get(identity)
    if item is None:
        say(output, "Unknown class. Use a taxonomy code or class id.")
        return
    say(output, f"{identity}: " + " | ".join(f"{lang}: {text}" for lang, text in item.captions))


def _primary_choice(scheme: Any, input_stream: TextIO, output: TextIO) -> str:
    while True:
        value = ask(
            input_stream,
            output,
            "Gold primary code/id (? roots, show CODE, s skip, f finish, q quit): ",
        )
        if value.lower() in {"s", "f", "q"}:
            return value.lower()
        if value == "?":
            for identity in scheme.children(None):
                _show_class(scheme, identity, output)
            say(output, "Use 'show 04.02' or make classification-tree RUN_ID=<run-id>.")
            continue
        if value.startswith("show "):
            _show_class(scheme, value[5:].strip(), output)
            continue
        resolved = scheme.resolve_code(value)
        if resolved is not None or value in scheme.classes:
            return value
        say(output, "Unknown class. Enter a taxonomy code, class id, or ?.")


def _candidate(
    row: dict[str, Any],
    extra: dict[str, Any],
    primary: str,
    alternates: str,
    scheme: Any,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "item_id": row["occurrence_id"],
        "gold_ref": f"{row['silo_id']}:{row['relative_path']}",
        "content_sha256": extra.get("content_hash"),
        "alternates": [item.strip() for item in alternates.split(",") if item.strip()],
    }
    record["primary_code" if scheme.resolve_code(primary) is not None else "primary"] = primary
    return record


def label_one(
    row: dict[str, Any],
    extra: dict[str, Any],
    scheme: Any,
    scheme_policy: Any,
    document_views: dict[str, str],
    input_stream: TextIO,
    output: TextIO,
) -> dict[str, Any] | str:
    """Prompt until one confirmed label or a skip/finish/quit command."""
    say(output, f"\nFile: {row['relative_path']}  ({row['occurrence_id']})")
    say(output, f"Preview: {review_preview(row, document_views)}")
    say(output, f"Classifier proposal (not gold): {row['primary_class_id']}")
    say(output, f"Evidence terms: {', '.join(evidence_terms(row)) or '[none]'}")
    if row["failure_reason"]:
        say(output, f"Extraction/decision reason: {row['failure_reason']}")
    while True:
        primary = _primary_choice(scheme, input_stream, output)
        if primary in {"s", "f", "q"}:
            return primary
        _show_class(scheme, primary, output)
        alternates = ask(
            input_stream, output, "Alternate class IDs, comma-separated (Enter none): "
        )
        record = _candidate(row, extra, primary, alternates, scheme)
        try:
            resolve_label(record, scheme, scheme_policy)
        except ValueError as error:
            say(output, f"Invalid label: {error}")
            continue
        if ask(input_stream, output, "Type yes to confirm this human gold label: ") == "yes":
            return record
        say(output, "Not recorded; choose again or skip.")
