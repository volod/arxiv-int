"""Shared containment rules for generation-scoped stage output roots."""

import json
from pathlib import Path

from arxiv_int.interfaces.pipeline import StageContext
from arxiv_int.runtime.containment import overlaps, resolve_allowed_path

CONTRACT_VERSION = "1.0.0"


def protect(candidate: Path, context: StageContext) -> None:
    """Refuse an output path that overlaps the project, silos, or protected roots."""
    roots = [
        Path(context.options["project_root"]).resolve(),
        *(silo.root.resolve() for silo in context.silos),
        *(
            Path(value).resolve()
            for value in json.loads(context.options.get("protected_roots", "[]"))
        ),
    ]
    if candidate == Path(candidate.anchor) or any(overlaps(candidate, root) for root in roots):
        raise ValueError("stage output overlaps protected roots")


def stage_output_root(context: StageContext, relative: str) -> Path:
    """Resolve one generation-scoped product root and refuse symlink traversal."""
    results = context.results_dir.resolve()
    protect(results, context)
    target = (
        results
        / f"{relative}/contract_version={CONTRACT_VERSION}"
        / f"generation_id={context.generation_id}"
    )
    resolved = resolve_allowed_path(target, (results,))
    if resolved != target:
        raise ValueError("stage output path must not traverse symlinks")
    return resolved


def stage_scratch(context: StageContext) -> Path:
    """Resolve and protect the bounded scratch directory for one stage."""
    scratch = Path(context.options.get("tmp_dir", str(context.results_dir / "tmp"))).resolve()
    protect(scratch, context)
    scratch.mkdir(parents=True, exist_ok=True)
    return scratch
