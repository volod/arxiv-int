"""Rewrite selected text, JSON, and JSONL together with remapped spans."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from arxiv_int.evaluation.bundles.manifest import canonical_json, json_line
from arxiv_int.evaluation.export.errors import ExportSpanError
from arxiv_int.evaluation.export.map import STRUCTURED_KEYS, AppliedSpan, SubstitutionTable
from arxiv_int.evaluation.export.policy import TRANSFORM_MARK

_SPAN_SOURCE_FIELDS = ("text", "query_text", "query", "context", "quote", "label")


@dataclass(frozen=True, slots=True)
class MappedText:
    """Rewritten text plus a monotonic old-to-new index map."""

    text: str
    old_to_new: tuple[int, ...]

    def map_span(self, start: int, end: int) -> tuple[int, int]:
        if start < 0 or end < start or end >= len(self.old_to_new):
            raise ExportSpanError(f"span [{start}:{end}] is outside the rewritten text")
        return self.old_to_new[start], self.old_to_new[end]


def rewrite_text(
    text: str,
    table: SubstitutionTable,
    *,
    spans: Sequence[AppliedSpan] = (),
) -> MappedText:
    """Replace unambiguous identities and span-bound same-name occurrences."""
    span_at = _span_index(spans)
    out: list[str] = []
    written = 0
    mapping = [0] * (len(text) + 1)
    index = 0
    while index < len(text):
        mapping[index] = written
        span = span_at.get(index)
        if span is not None:
            written += _emit_span(text, index, span, out)
            _fill_interior(mapping, index, span.end, written)
            index = span.end
            continue
        matched = _unambiguous_at(text, index, table.replacements, spans)
        if matched is not None:
            original, substitute = matched
            out.append(substitute)
            written += len(substitute)
            _fill_interior(mapping, index, index + len(original), written)
            index += len(original)
            continue
        _refuse_unbound_ambiguous(text, index, table.ambiguous)
        out.append(text[index])
        written += 1
        index += 1
    mapping[len(text)] = written
    return MappedText("".join(out), tuple(mapping))


def rewrite_json_value(
    value: object,
    table: SubstitutionTable,
    artifact_maps: Mapping[str, MappedText],
) -> object:
    """Recursively rewrite JSON strings, keys, and span coordinates."""
    if isinstance(value, str):
        return rewrite_text(value, table).text
    if isinstance(value, list):
        return [rewrite_json_value(item, table, artifact_maps) for item in value]
    if isinstance(value, dict):
        return _rewrite_object(value, table, artifact_maps)
    return value


def encode_json(value: object) -> bytes:
    """Serialize rewritten JSON with stable keys."""
    return canonical_json(value)


def encode_jsonl(rows: Sequence[object]) -> bytes:
    """Serialize rewritten JSONL rows with stable keys."""
    return b"".join(json_line(row) for row in rows)


def mark_transformed_manifest(
    payload: dict[str, Any], artifacts: Mapping[str, tuple[str, int]]
) -> dict[str, Any]:
    """Rebuild checksums and mark the copy as transformed data."""
    updated = dict(payload)
    configuration = (
        dict(updated.get("configuration") or {})
        if isinstance(updated.get("configuration"), dict)
        else {}
    )
    configuration["identity_transform"] = dict(TRANSFORM_MARK)
    updated["configuration"] = configuration
    updated["data_class"] = TRANSFORM_MARK["data_class"]
    if artifacts:
        updated["artifacts"] = {
            name: {"bytes": size, "sha256": digest}
            for name, (digest, size) in sorted(artifacts.items())
        }
    return updated


def _rewrite_object(
    original: dict[str, object],
    table: SubstitutionTable,
    artifact_maps: Mapping[str, MappedText],
) -> dict[str, object]:
    field_maps: dict[str, MappedText] = {}
    rewritten: dict[str, object] = {}
    entity_id = original.get("entity_id") or original.get("object_id") or original.get("id")
    bound = entity_id if isinstance(entity_id, str) and entity_id in table.entity_labels else None
    for key, value in original.items():
        new_key = rewrite_text(str(key), table).text
        if isinstance(value, str):
            mapped = _rewrite_string_field(str(key), value, table, bound)
            field_maps[str(key)] = mapped
            rewritten[new_key] = mapped.text
        else:
            rewritten[new_key] = rewrite_json_value(value, table, artifact_maps)
    return _remap_span_object(original, rewritten, artifact_maps, field_maps)


def _rewrite_string_field(
    key: str, value: str, table: SubstitutionTable, bound_entity: str | None
) -> MappedText:
    if key in STRUCTURED_KEYS and value in table.structured:
        substitute = table.structured[value]
        mapping = [0] * (len(value) + 1)
        mapping[len(value)] = len(substitute)
        return MappedText(substitute, tuple(mapping))
    spans: tuple[AppliedSpan, ...] = ()
    if bound_entity is not None:
        spans = bind_entity_surfaces(value, bound_entity, table)
    return rewrite_text(value, table, spans=spans)


def bind_entity_surfaces(
    text: str, entity_id: str, table: SubstitutionTable
) -> tuple[AppliedSpan, ...]:
    """Bind same-name surfaces in one JSON string to a declared entity."""
    surfaces = sorted(table.entity_surfaces.get(entity_id, ()), key=len, reverse=True)
    used = [False] * len(text)
    spans: list[AppliedSpan] = []
    substitute = table.entity_labels[entity_id]
    for surface in surfaces:
        start = 0
        while True:
            index = text.find(surface, start)
            if index < 0:
                break
            end = index + len(surface)
            if surface and not any(used[index:end]):
                used[index:end] = [True] * (end - index)
                spans.append(AppliedSpan("json", index, end, surface, substitute, entity_id))
            start = index + 1
    return tuple(sorted(spans, key=lambda item: item.start))


def _remap_span_object(
    original: dict[str, object],
    rewritten: dict[str, object],
    artifact_maps: Mapping[str, MappedText],
    field_maps: Mapping[str, MappedText],
) -> dict[str, object]:
    start = original.get("start")
    end = original.get("end")
    if not isinstance(start, int) or not isinstance(end, int) or isinstance(start, bool):
        return rewritten
    mapped = _span_source_map(original, artifact_maps, field_maps)
    if mapped is None:
        quote = original.get("quote") or original.get("text")
        new_quote = rewritten.get("quote") or rewritten.get("text")
        if (
            isinstance(quote, str)
            and isinstance(new_quote, str)
            and start == 0
            and end == len(quote)
        ):
            rewritten["start"] = 0
            rewritten["end"] = len(new_quote)
        return rewritten
    new_start, new_end = mapped.map_span(start, end)
    rewritten["start"] = new_start
    rewritten["end"] = new_end
    return rewritten


def _span_source_map(
    original: dict[str, object],
    artifact_maps: Mapping[str, MappedText],
    field_maps: Mapping[str, MappedText],
) -> MappedText | None:
    artifact = original.get("artifact") or original.get("source")
    if isinstance(artifact, str) and artifact in artifact_maps:
        return artifact_maps[artifact]
    for field in _SPAN_SOURCE_FIELDS:
        if field in field_maps:
            return field_maps[field]
    return None


def _span_index(spans: Sequence[AppliedSpan]) -> dict[int, AppliedSpan]:
    index: dict[int, AppliedSpan] = {}
    for span in spans:
        if span.start in index:
            raise ExportSpanError("duplicate identity span start")
        index[span.start] = span
    return index


def _emit_span(text: str, index: int, span: AppliedSpan, out: list[str]) -> int:
    if text[index : span.end] != span.original:
        raise ExportSpanError("identity span text does not match the catalog")
    out.append(span.substitute)
    return len(span.substitute)


def _unambiguous_at(
    text: str,
    index: int,
    replacements: Sequence[tuple[str, str]],
    spans: Sequence[AppliedSpan],
) -> tuple[str, str] | None:
    for original, substitute in replacements:
        if not text.startswith(original, index):
            continue
        consumed = index + len(original)
        if any(index < span.start < consumed for span in spans):
            raise ExportSpanError("identity replacement overlaps a catalog span")
        return original, substitute
    return None


def _refuse_unbound_ambiguous(text: str, index: int, ambiguous: frozenset[str]) -> None:
    for original in sorted(ambiguous, key=len, reverse=True):
        if text.startswith(original, index):
            raise ExportSpanError("same-name identity occurs without a catalog span")


def _fill_interior(mapping: list[int], start: int, end: int, written: int) -> None:
    for consumed in range(start + 1, end):
        mapping[consumed] = written
