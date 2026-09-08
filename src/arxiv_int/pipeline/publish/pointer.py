"""Active generation and catalog pointers with crash injection and orphan cleanup."""

import os
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

from arxiv_int.contracts.generate.normalize import normalize_json
from arxiv_int.pipeline.locking import pipeline_lock
from arxiv_int.pipeline.persist import load_json, run_dir, write_json
from arxiv_int.pipeline.publish.assemble import fingerprint_document
from arxiv_int.pipeline.publish.codec import document_from_payload, document_payload
from arxiv_int.pipeline.publish.model import (
    ACTIVE_CATALOG,
    ACTIVE_GENERATION,
    KNOWLEDGE_BASE_NAME,
    KnowledgeBase,
)

Injector = Callable[[str], None]


class ActivationRefusedError(RuntimeError):
    """Raised when a non-complete generation tries to become active."""


def knowledge_base_path(runs_dir: Path, run_id: str) -> Path:
    """Return ``$RUNS_DIR/<run-id>/knowledge-base.json``."""
    return run_dir(runs_dir, run_id) / KNOWLEDGE_BASE_NAME


def save_knowledge_base(runs_dir: Path, document: KnowledgeBase) -> Path:
    """Atomically write the generation manifest under the run."""
    path = knowledge_base_path(runs_dir, document.run_id)
    write_json(path, document_payload(document))
    return path


def load_knowledge_base(runs_dir: Path, run_id: str) -> KnowledgeBase:
    """Load a previously written generation manifest."""
    return document_from_payload(load_json(knowledge_base_path(runs_dir, run_id)))


def load_active_generation(runs_dir: Path) -> dict[str, Any] | None:
    """Return the current file-side active generation pointer, if any."""
    path = runs_dir / ACTIVE_GENERATION
    if not path.is_file():
        return None
    return load_json(path)


def activate_generation(
    runs_dir: Path,
    document: KnowledgeBase,
    *,
    injector: Injector | None = None,
) -> KnowledgeBase:
    """Switch file and catalog pointers only for a complete requested profile."""
    with pipeline_lock(runs_dir):
        return _activate_generation(runs_dir, document, injector)


def _activate_generation(
    runs_dir: Path,
    document: KnowledgeBase,
    injector: Injector | None,
) -> KnowledgeBase:
    if document.status != "succeeded":
        raise ActivationRefusedError(f"refusing to activate generation status={document.status}")
    if fingerprint_document(document) != document.fingerprint:
        raise ActivationRefusedError("knowledge-base fingerprint mismatch")
    snapshot = Path(document.run_id) / "publications" / document.fingerprint
    catalog = snapshot / ACTIVE_CATALOG
    sealed = replace(document, active=True, catalog_path=str(catalog))
    save_knowledge_base(runs_dir, document)
    write_json(runs_dir / snapshot / KNOWLEDGE_BASE_NAME, document_payload(sealed))
    _hit(injector, "after-manifest")
    _atomic_pointer(
        runs_dir / catalog,
        _catalog_payload(document),
        injector,
        "after-catalog-write",
        "after-catalog-replace",
    )
    payload = _generation_payload(document)
    payload["catalog"] = str(catalog)
    payload["manifest"] = str(snapshot / KNOWLEDGE_BASE_NAME)
    _atomic_pointer(
        runs_dir / ACTIVE_GENERATION,
        payload,
        injector,
        "after-generation-write",
        "after-generation-replace",
    )
    save_knowledge_base(runs_dir, sealed)
    return sealed


def reconcile_orphans(root: Path) -> int:
    """Remove leftover sibling temp files after a crashed publication."""
    with pipeline_lock(root):
        removed = 0
        # Only publication-owned temps; preserve worker staging and other run artifacts.
        candidates = [root / f".{ACTIVE_GENERATION}.tmp"]
        candidates.extend(root.glob("*/publications/*/.*.tmp"))
        for path in candidates:
            if path.is_file():
                path.unlink()
                removed += 1
        return removed


def _atomic_pointer(
    path: Path,
    payload: dict[str, Any],
    injector: Injector | None,
    after_write: str,
    after_replace: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(normalize_json(payload), encoding="utf-8")
    _hit(injector, after_write)
    os.replace(tmp, path)
    _hit(injector, after_replace)


def _catalog_payload(document: KnowledgeBase) -> dict[str, Any]:
    return {
        "generation_id": document.generation_id,
        "profile": document.profile,
        "run_id": document.run_id,
        "status": document.status,
    }


def _generation_payload(document: KnowledgeBase) -> dict[str, Any]:
    return {
        "catalog": ACTIVE_CATALOG,
        "generation_id": document.generation_id,
        "manifest": f"{document.run_id}/{KNOWLEDGE_BASE_NAME}",
        "profile": document.profile,
        "run_id": document.run_id,
    }


def _hit(injector: Injector | None, point: str) -> None:
    if injector is not None:
        injector(point)
