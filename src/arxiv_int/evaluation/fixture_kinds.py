"""Stable identities for frozen evaluation families, splits, and data classes."""

SCHEMA_VERSION = 1
FIXTURE_CONTRACT_VERSION = "1.0.0"
FIXTURE_DATASET_ID = "evaluation-items"
FIXTURE_GENERATION_ID = "eval-found-fixtures-v1"

SPLIT_TUNING = "tuning"
SPLIT_FINAL = "final"
SPLITS = frozenset({SPLIT_TUNING, SPLIT_FINAL})

DATA_CLASS_RAW = "raw"
DATA_CLASS_TRANSFORMED = "transformed"
METRIC_CLASS_STRUCTURAL = "structural"
METRIC_CLASS_HELD_OUT = "held-out"

KIND_EXTRACTION = "extraction"
KIND_CLASSIFICATION = "classification"
KIND_RUSSIAN_RETRIEVAL = "russian-retrieval"
KIND_SEMANTIC = "semantic"
KIND_ENTITY = "entity"
KIND_FACT = "fact"
KIND_ONTOLOGY = "ontology"
KIND_GRAPH = "graph"
KIND_DOMAIN_ARTIFACT = "domain-artifact"
KIND_CATALOG = "catalog"
KIND_ANOMALY = "anomaly"
KIND_REPORTING = "reporting"
KIND_GEOTEMPORAL = "geotemporal"
KIND_DOMAIN_NEGATIVE = "domain-negative"

ITEM_KINDS = (
    KIND_EXTRACTION,
    KIND_CLASSIFICATION,
    KIND_RUSSIAN_RETRIEVAL,
    KIND_SEMANTIC,
    KIND_ENTITY,
    KIND_FACT,
    KIND_ONTOLOGY,
    KIND_GRAPH,
    KIND_DOMAIN_ARTIFACT,
    KIND_CATALOG,
    KIND_ANOMALY,
    KIND_REPORTING,
    KIND_GEOTEMPORAL,
    KIND_DOMAIN_NEGATIVE,
)

EXCEPTIONAL_CLASSES = frozenset({"unclassified", "unreadable"})
ONTOLOGY_ACTIONS = frozenset({"add", "deprecate", "draft", "contradiction"})
ANOMALY_COHORTS = frozenset({"positive", "hard-negative", "insufficient", "time-leakage"})

THRESHOLD_ADOPT = 0.9
THRESHOLD_REVIEW_BUDGET = 0.5
RETRIEVAL_K = 5
LATENCY_P95 = 95.0
DEFAULT_BOOTSTRAP_SEED = 13

# Synthetic labels that must never appear in Git-bound proof summaries.
SYNTHETIC_IDENTITY_TOKENS = {
    "person": "Fixture Person",
    "company": "Fixture Company",
}
