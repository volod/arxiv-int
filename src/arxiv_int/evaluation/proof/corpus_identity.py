"""Current corpus producer identities and portable artifact references."""

from pathlib import Path
from typing import Any

from arxiv_int.evaluation.bundles.layout import digest_bytes
from arxiv_int.evaluation.bundles.manifest import canonical_json
from arxiv_int.evaluation.proof.corpus_artifacts import STAGES, artifact_record, require
from arxiv_int.pipeline.control.fingerprints import reuse_key
from arxiv_int.pipeline.control.model_assets import docling_asset_fingerprint
from arxiv_int.pipeline.dag.execute import stage_identity
from arxiv_int.pipeline.dag.registry import StageRegistry
from arxiv_int.pipeline.reconcile.scan import bind_shard
from arxiv_int.pipeline.run.context import RunContext


def corpus_fingerprints(
    context: RunContext, registry: StageRegistry
) -> tuple[dict[str, str], dict[str, Any]]:
    """Capture every stage's owned identities, including actual model bytes."""
    context = bind_shard(context, "default")
    stages: dict[str, Any] = {}
    keys: dict[str, str] = {}
    for name in ("preflight", *STAGES):
        spec = registry.get(name)
        identity = stage_identity(spec, context, tuple(keys[parent] for parent in spec.depends_on))
        keys[name] = reuse_key(identity)
        stages[name] = {
            "reuse_key": keys[name],
            "owned": dict(identity.owned),
            "tools": dict(spec.tools),
        }
    code = {p.name: artifact_record(p) for p in sorted(Path(__file__).parent.glob("corpus_*.py"))}
    return {
        "code": digest_bytes(canonical_json(code)),
        "producers": digest_bytes(canonical_json(stages)),
        "docling_assets": docling_asset_fingerprint(
            Path(context.secret_free.get("MODEL_CACHE_DIR", str(context.results_dir / "models")))
        ),
        "source": context.source_snapshot,
        "configuration": context.config_fingerprint,
    }, stages


def reference(path: Path, context: RunContext) -> str:
    """Encode operator-owned paths relative to their configured root."""
    for name, root in (("runs", context.runs_dir), ("results", context.results_dir)):
        if path.is_relative_to(root):
            return f"{name}/{path.relative_to(root).as_posix()}"
    raise ValueError("proof artifact is outside configured result roots")


def resolve_reference(value: str, context: RunContext) -> Path:
    """Refuse escaped or symlinked proof references before accessing them."""
    relative = Path(value)
    require(not relative.is_absolute() and ".." not in relative.parts, "invalid proof reference")
    roots = {"runs": context.runs_dir, "results": context.results_dir}
    require(bool(relative.parts) and relative.parts[0] in roots, "unknown proof reference root")
    root = roots[relative.parts[0]].resolve()
    path = root.joinpath(*relative.parts[1:])
    require(path.resolve() == path and path.is_relative_to(root), "symlinked proof reference")
    return path
