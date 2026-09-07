"""Extraction, classification, and reporting fixture families."""

from arxiv_int.evaluation.fixture_build import family, item, pair_splits
from arxiv_int.evaluation.fixture_kinds import (
    KIND_CLASSIFICATION,
    KIND_EXTRACTION,
    KIND_REPORTING,
    SPLIT_FINAL,
    SPLIT_TUNING,
)
from arxiv_int.evaluation.fixture_model import GoldFamily


def extraction_family() -> GoldFamily:
    """File-format extraction with anchors, tables, and quarantine failures."""
    text_gold = {
        "anchors": [{"document_id": "doc-text", "end": 24, "page": 1, "start": 0}],
        "expected": ["contract number 42"],
        "format": "text",
        "table_cells": [],
    }
    pdf_gold = {
        "anchors": [{"document_id": "doc-pdf", "end": 18, "page": 2, "start": 4}],
        "expected": ["amount 100 kg"],
        "format": "pdf",
        "table_cells": [{"col": 1, "row": 0, "text": "100 kg"}],
    }
    fail_gold = {
        "anchors": [],
        "expected": [],
        "failure": "unreadable",
        "format": "image",
        "table_cells": [],
    }
    text_pair = pair_splits(
        item_kind=KIND_EXTRACTION,
        stem="extract-text",
        gold=text_gold,
        positive={"predicted": ["contract number 42"], "spans": text_gold["anchors"]},
        negative={"predicted": ["unrelated title"], "spans": []},
        source="fixture://extract/text.txt",
        evidence="span:doc-text:0:24",
        query_text="extract contract number",
        extra_gold={**text_gold, "expected": ["contract number 99"]},
        extra_positive={"predicted": ["contract number 99"], "spans": text_gold["anchors"]},
        extra_query="extract later contract number",
    )
    pdf_item = item(
        item_id="extract-pdf-table-tuning",
        item_kind=KIND_EXTRACTION,
        split=SPLIT_TUNING,
        gold_ref="gold:extract-pdf:tuning",
        gold=pdf_gold,
        positive={"predicted": ["amount 100 kg"], "spans": pdf_gold["anchors"]},
        negative={"predicted": ["amount 5 kg"], "spans": []},
        source="fixture://extract/table.pdf",
        evidence="page:2:cell:0,1",
        query_text="extract table amount",
    )
    fail_item = item(
        item_id="extract-unreadable-final",
        item_kind=KIND_EXTRACTION,
        split=SPLIT_FINAL,
        gold_ref="gold:extract-fail:final",
        gold=fail_gold,
        positive={"predicted": [], "failure": "unreadable"},
        negative={"predicted": ["hallucinated text"], "failure": None},
        source="fixture://extract/scan.bin",
        evidence="quarantine:unreadable",
        query_text="extract scanned binary",
    )
    return family(KIND_EXTRACTION, (*text_pair, pdf_item, fail_item))


def classification_family() -> GoldFamily:
    """Hierarchical labels plus unclassified and unreadable outcomes."""
    primary = {
        "alternate": ["62"],
        "path": ["6", "62", "621"],
        "primary": "621",
    }
    unclassified = {"alternate": [], "path": ["unclassified"], "primary": "unclassified"}
    unreadable = {"alternate": [], "path": ["unreadable"], "primary": "unreadable"}
    tuning, final = pair_splits(
        item_kind=KIND_CLASSIFICATION,
        stem="class-hierarchy",
        gold=primary,
        positive={"path": ["6", "62", "621"], "primary": "621"},
        negative={"path": ["5", "51"], "primary": "51"},
        source="fixture://classify/drawing.pdf",
        evidence="inventory:file-1",
        label="621",
        extra_gold={
            "alternate": ["621.3"],
            "path": ["6", "62", "621", "621.3"],
            "primary": "621.3",
        },
    )
    exceptional = item(
        item_id="class-unclassified-final",
        item_kind=KIND_CLASSIFICATION,
        split=SPLIT_FINAL,
        gold_ref="gold:class-unclassified:final",
        gold=unclassified,
        positive={"path": ["unclassified"], "primary": "unclassified"},
        negative={"path": ["6", "62"], "primary": "62"},
        source="fixture://classify/unknown.bin",
        evidence="inventory:file-unknown",
        label="unclassified",
    )
    broken = item(
        item_id="class-unreadable-tuning",
        item_kind=KIND_CLASSIFICATION,
        split=SPLIT_TUNING,
        gold_ref="gold:class-unreadable:tuning",
        gold=unreadable,
        positive={"path": ["unreadable"], "primary": "unreadable"},
        negative={"path": ["6"], "primary": "6"},
        source="fixture://classify/corrupt.pdf",
        evidence="inventory:file-corrupt",
        label="unreadable",
    )
    return family(KIND_CLASSIFICATION, (tuning, final, exceptional, broken))


def reporting_family() -> GoldFamily:
    """Coverage rows that must cite evidence and denominators."""
    gold = {
        "cited": True,
        "coverage": 1.0,
        "denominator": 4,
        "family": "catalogs",
        "numerator": 4,
    }
    tuning = item(
        item_id="report-coverage-tuning",
        item_kind=KIND_REPORTING,
        split=SPLIT_TUNING,
        gold_ref="gold:report-coverage:tuning",
        gold=gold,
        positive=gold,
        negative={**gold, "cited": False, "coverage": 1.0, "numerator": 4},
        source="fixture://report/index.json",
        evidence="report:row:catalogs",
        query_text="catalog coverage",
    )
    final = item(
        item_id="report-empty-family-final",
        item_kind=KIND_REPORTING,
        split=SPLIT_FINAL,
        gold_ref="gold:report-empty:final",
        gold={
            "cited": True,
            "coverage": 0.0,
            "denominator": 3,
            "family": "anomalies",
            "numerator": 0,
        },
        positive={
            "cited": True,
            "coverage": 0.0,
            "denominator": 3,
            "family": "anomalies",
            "numerator": 0,
        },
        negative={
            "cited": False,
            "coverage": 1.0,
            "denominator": 3,
            "family": "anomalies",
            "numerator": 3,
        },
        source="fixture://report/index.json",
        evidence="report:row:anomalies",
        query_text="anomaly coverage empty",
    )
    return family(KIND_REPORTING, (tuning, final))
