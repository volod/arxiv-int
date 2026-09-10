"""Stable defaults shared by reusable evaluation metrics."""

EXCEPTIONAL_CLASSES = frozenset({"unclassified", "unreadable"})
LATENCY_P95 = 95.0
RETRIEVAL_K = 5
THRESHOLD_REVIEW_BUDGET = 0.5

DATA_CLASS_RAW = "raw"
DATA_CLASS_TRANSFORMED = "transformed"
METRIC_CLASS_HELD_OUT = "held-out"
METRIC_CLASS_STRUCTURAL = "structural"
