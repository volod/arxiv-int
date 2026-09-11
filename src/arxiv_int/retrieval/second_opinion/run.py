"""Run one lexical second-opinion stage: development, preregister, or final."""

import logging
from dataclasses import dataclass
from itertools import chain
from pathlib import Path

from sqlalchemy import create_engine

from arxiv_int.contracts.generate.normalize import sha256_text
from arxiv_int.evaluation.bundles.errors import BundleExistsError
from arxiv_int.retrieval.second_opinion.database import (
    build_indexes,
    load_base,
    paradedb_version,
    run_queries,
    tokenizer_fingerprint,
)
from arxiv_int.retrieval.second_opinion.decision import VERDICT_ADOPT, comparisons, decide
from arxiv_int.retrieval.second_opinion.filler import filler_rows
from arxiv_int.retrieval.second_opinion.model import (
    SPLIT_DEVELOPMENT,
    SPLIT_FINAL,
    Execution,
    Protocol,
    SplitData,
)
from arxiv_int.retrieval.second_opinion.protocol import index_text_fields, load_protocol
from arxiv_int.retrieval.second_opinion.publish import (
    publish_execution,
    publish_preregistration,
    stage_directory,
    verify_preregistration,
)
from arxiv_int.retrieval.second_opinion.scoring import score_case
from arxiv_int.retrieval.second_opinion.splits import (
    FillerVocabulary,
    load_filler,
    load_split,
    require_distinct,
)
from arxiv_int.stores.projections.adapters.lexical import TOKENIZER_FINGERPRINT

_LOG = logging.getLogger(__name__)
STAGE_PREREGISTER = "preregister"
STAGES = (SPLIT_DEVELOPMENT, STAGE_PREREGISTER, SPLIT_FINAL)


@dataclass(frozen=True, slots=True)
class Overrides:
    """Development-only cost overrides; the final stage refuses every override."""

    filler_chunks: int | None = None
    build_repetitions: int | None = None
    query_repetitions: int | None = None

    def active(self) -> bool:
        """Return whether any override is set."""
        return any(
            v is not None
            for v in (self.filler_chunks, self.build_repetitions, self.query_repetitions)
        )


@dataclass(frozen=True, slots=True)
class StageOutcome:
    """Published stage identity and the selected-arm decision."""

    stage: str
    bundle_dir: Path
    manifest_fingerprint: str
    verdict: str
    selected_arm: str
    reindex_required: bool
    engine_version: str


def run_stage(
    *,
    project_root: Path,
    database_url: str,
    runs_dir: Path,
    run_id: str,
    stage: str,
    overrides: Overrides | None = None,
) -> StageOutcome:
    """Validate frozen inputs, then run and publish exactly one stage."""
    chosen = overrides or Overrides()
    if stage not in STAGES:
        raise ValueError(f"unknown second-opinion stage {stage!r}; use one of {STAGES}")
    if not run_id.strip() or run_id.strip() != run_id:
        raise ValueError("run_id must be non-empty without surrounding whitespace")
    if stage != SPLIT_DEVELOPMENT and chosen.active():
        raise ValueError("only the development stage accepts cost overrides")
    protocol = load_protocol(project_root)
    development = load_split(project_root, protocol, SPLIT_DEVELOPMENT)
    final = load_split(project_root, protocol, SPLIT_FINAL)
    require_distinct(development, final)
    vocabulary = load_filler(project_root, protocol)
    if stage == STAGE_PREREGISTER:
        published = publish_preregistration(project_root, runs_dir, run_id, protocol, final)
        return StageOutcome(
            stage, published.directory, published.fingerprint, "preregistered",
            protocol.candidate, reindex_required(protocol, protocol.candidate), "",
        )  # fmt: skip
        # A candidate's reindex need is known before execution; the decision is not.
    extra: dict[str, object] = {}
    if stage == SPLIT_FINAL:
        extra["preregistration"] = verify_preregistration(project_root, runs_dir, run_id, protocol)
    destination = stage_directory(runs_dir, run_id, stage)
    if destination.exists() or destination.is_symlink():
        raise BundleExistsError(f"run bundle already exists: {destination}")
    split = development if stage == SPLIT_DEVELOPMENT else final
    execution = execute_split(
        database_url, protocol, split, vocabulary, run_id=run_id, overrides=chosen
    )
    scores = {(score.arm_id, score.case_id): score for score in execution.scores}
    decision = decide(protocol, split, execution.runs, scores)
    selected = protocol.candidate if decision.verdict == VERDICT_ADOPT else protocol.baseline
    reindex = reindex_required(protocol, selected)
    extra.update({"reindex_required": reindex, "selected_arm": selected, "stage": stage})
    compared = comparisons(protocol, split, scores)
    published = publish_execution(
        project_root, runs_dir, run_id, stage, protocol, execution, decision, compared, extra
    )
    return StageOutcome(
        stage, published.directory, published.fingerprint, decision.verdict, selected, reindex,
        execution.engine_version,
    )  # fmt: skip


def execute_split(
    database_url: str,
    protocol: Protocol,
    split: SplitData,
    vocabulary: FillerVocabulary,
    *,
    run_id: str,
    overrides: Overrides,
) -> Execution:
    """Load, build, and query every arm inside one rolled-back transaction."""
    token = sha256_text(f"{run_id}:{split.name}")[:10]
    filler = protocol.filler
    chunks = (
        overrides.filler_chunks if overrides.filler_chunks is not None else int(filler["chunks"])
    )
    builds = overrides.build_repetitions or protocol.execution["build_repetitions"]
    queries = overrides.query_repetitions or protocol.execution["query_repetitions"]
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                version = paradedb_version(connection)
                if version != protocol.paradedb_version:
                    raise ValueError(
                        f"pg_search {version} is not the pinned {protocol.paradedb_version}"
                    )
                judged = ({**_row(chunk)} for chunk in split.chunks)
                generated = filler_rows(
                    vocabulary,
                    chunks=chunks,
                    min_words=int(filler["min_words"]),
                    max_words=int(filler["max_words"]),
                    stopword_share=filler["stopword_share"],
                    seed=int(filler["seed"]),
                )
                base, rows = load_base(connection, token, chain(judged, generated))
                _LOG.info("second-opinion %s loaded %d rows", split.name, rows)
                profiles = {arm.index_profile for arm in protocol.arms}
                targets, readings = build_indexes(
                    connection,
                    base,
                    {name: protocol.index_profiles[name] for name in profiles},
                    token=token,
                    rows=rows,
                    repetitions=builds,
                    seed=protocol.execution["order_seed"],
                )
                runs = run_queries(
                    connection,
                    protocol.arms,
                    targets,
                    split.cases,
                    k=max(protocol.k_quality, protocol.k_precision),
                    repetitions=queries,
                    warmup=protocol.execution["warmup_queries"],
                    seed=protocol.execution["order_seed"],
                )
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
    by_chunk = {chunk.chunk_id: chunk for chunk in split.chunks}
    by_case = {case.case_id: case for case in split.cases}
    scores = tuple(
        score_case(
            by_case[run.case_id], run, by_chunk,
            k_quality=protocol.k_quality, k_precision=protocol.k_precision,
        )
        for run in runs
    )  # fmt: skip
    repetitions = {"build": builds, "query": queries, "filler_chunks": chunks}
    return Execution(split, version, rows - len(split.chunks), readings, runs, scores, repetitions)


def reindex_required(protocol: Protocol, arm_id: str) -> bool:
    """Return whether serving one arm needs a lexical projection rebuild."""
    index_profile = next(arm.index_profile for arm in protocol.arms if arm.arm_id == arm_id)
    fields = index_text_fields(protocol.index_profiles[index_profile])
    return tokenizer_fingerprint(fields) != TOKENIZER_FINGERPRINT


def _row(chunk: object) -> dict[str, object]:
    return {
        name: getattr(chunk, name)
        for name in ("chunk_id", "document_id", "title", "body", "identifiers", "language")
    }
