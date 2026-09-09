"""Russian lexical and semantic retrieval fixture families."""

from arxiv_int.evaluation.fixtures.build import family, item, pair_splits
from arxiv_int.evaluation.fixtures.kinds import (
    KIND_RUSSIAN_RETRIEVAL,
    KIND_SEMANTIC,
    SPLIT_FINAL,
    SPLIT_TUNING,
)
from arxiv_int.evaluation.fixtures.model import GoldFamily
from arxiv_int.evaluation.scoring.payload import as_int, as_str


def _span(document_id: str, start: int, end: int) -> dict[str, object]:
    return {"document_id": document_id, "end": end, "start": start}


def _chunk(document_id: str, start: int, end: int, text: str, rank: int) -> dict[str, object]:
    return {
        "document_id": document_id,
        "end": end,
        "rank": rank,
        "start": start,
        "text": text,
    }


def russian_retrieval_family() -> GoldFamily:
    """Inflection, identifiers, OCR, e/yo, keyboard-layout, and mixed queries."""
    cases = (
        (
            "ru-inflection",
            "dogovory postavki",
            "document mentions dogovor postavki",
            _span("ru-1", 10, 26),
            SPLIT_TUNING,
        ),
        (
            "ru-identifier",
            "INN 0123456789",
            "taxpayer INN 0123456789 recorded",
            _span("ru-2", 14, 24),
            SPLIT_FINAL,
        ),
        (
            "ru-abbrev",
            "OOO Fixture Co",
            "obshchestvo s ogranichennoi otvetstvennostyu Fixture Co",
            _span("ru-3", 46, 57),
            SPLIT_TUNING,
        ),
        (
            "ru-ocr",
            "d0govor nomer 7",
            "dogovor nomer 7 signed",
            _span("ru-4", 0, 14),
            SPLIT_FINAL,
        ),
        (
            "ru-eyo",
            "vsyo eshche deistvuet",
            "vse eshche deistvuet clause",
            _span("ru-5", 0, 16),
            SPLIT_TUNING,
        ),
        (
            "ru-keyboard",
            "ljujdjp",
            "dogovor scanned from a Russian keyboard layout",
            _span("ru-6", 0, 7),
            SPLIT_FINAL,
        ),
        (
            "ru-mixed",
            "invoice schet 42",
            "mixed-language invoice schet 42",
            _span("ru-7", 16, 31),
            SPLIT_TUNING,
        ),
    )
    items = []
    for stem, query, text, span, split in cases:
        hit = _chunk(
            as_str(span["document_id"]), as_int(span["start"]), as_int(span["end"]), text, 1
        )
        miss = _chunk("other", 0, 12, "unrelated English memo", 1)
        items.append(
            item(
                item_id=f"{stem}-{split}",
                item_kind=KIND_RUSSIAN_RETRIEVAL,
                split=split,
                gold_ref=f"gold:{stem}:{split}",
                gold={"k": 5, "spans": [span]},
                positive={"chunks": [hit]},
                negative={"chunks": [miss]},
                source=f"fixture://lexical/{stem}.txt",
                evidence=f"span:{span['document_id']}:{span['start']}:{span['end']}",
                query_text=query,
            )
        )
    return family(KIND_RUSSIAN_RETRIEVAL, tuple(items))


def semantic_family() -> GoldFamily:
    """Multi-hop queries that must cite exact source spans."""
    hop_spans = [_span("sem-a", 0, 12), _span("sem-b", 20, 36)]
    hops = [
        _chunk("sem-a", 0, 12, "supplier Alpha", 1),
        _chunk("sem-b", 20, 36, "ships Pump-100", 2),
    ]
    tuning, final = pair_splits(
        item_kind=KIND_SEMANTIC,
        stem="semantic-multihop",
        gold={"hops": 2, "k": 5, "spans": hop_spans},
        positive={"chunks": hops},
        negative={"chunks": [_chunk("sem-z", 0, 10, "unrelated", 1)]},
        source="fixture://semantic/graph.txt",
        evidence="span:sem-a:0:12+sem-b:20:36",
        query_text="who ships Pump-100 for supplier Alpha",
        extra_gold={"hops": 2, "k": 5, "spans": [_span("sem-c", 4, 18), _span("sem-d", 8, 22)]},
        extra_positive={
            "chunks": [
                _chunk("sem-c", 4, 18, "supplier Beta", 1),
                _chunk("sem-d", 8, 22, "pays invoice 88", 2),
            ]
        },
        extra_query="who pays invoice 88 for supplier Beta",
    )
    empty = item(
        item_id="semantic-no-evidence-final",
        item_kind=KIND_SEMANTIC,
        split=SPLIT_FINAL,
        gold_ref="gold:semantic-empty:final",
        gold={"hops": 1, "k": 5, "spans": [_span("sem-empty", 0, 8)]},
        positive={"chunks": [_chunk("sem-empty", 0, 8, "present", 1)]},
        negative={"chunks": []},
        source="fixture://semantic/empty.txt",
        evidence="span:sem-empty:0:8",
        query_text="missing hop should not score",
    )
    return family(KIND_SEMANTIC, (tuning, final, empty))
