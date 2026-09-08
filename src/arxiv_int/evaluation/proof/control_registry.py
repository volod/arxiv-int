"""Fixture DAG used to prove pipeline-control mechanics on a disposable copy."""

from pathlib import Path

from arxiv_int.contracts.generate.normalize import sha256_text
from arxiv_int.evaluation.bundles.layout import digest_bytes
from arxiv_int.evaluation.proof.control_copy import CAPABILITY_ID
from arxiv_int.pipeline.dag.registry import ResourceEstimate, StageRegistry, StageSpec
from arxiv_int.pipeline.publish.preflight import PreflightStage
from arxiv_int.pipeline.run.fixtures import FixtureStage

SCENARIO_VERSION = "1"
CONTROL_PROFILE_STAGES: tuple[str, ...] = ("preflight", "alpha", "beta", "gamma")
CONTROL_OPTIONAL: frozenset[str] = frozenset({"omega"})
_CODE_ROOTS = (
    ("src", "arxiv_int", "evaluation", "proof"),
    ("src", "arxiv_int", "pipeline"),
)


def control_scenario_fingerprint() -> str:
    """Return the stable identity of this proof scenario, not evaluation fixtures."""
    return sha256_text(f"{CAPABILITY_ID}:{SCENARIO_VERSION}")


def control_code_fingerprint(project_root: Path) -> str:
    """Hash pipeline and proof Python sources so stale proofs can be detected."""
    blobs: list[bytes] = []
    for parts in _CODE_ROOTS:
        root = project_root.joinpath(*parts)
        if not root.is_dir():
            continue
        blobs.extend(path.read_bytes() for path in sorted(root.rglob("*.py")))
    return digest_bytes(b"".join(blobs))


def control_proof_fingerprints(project_root: Path) -> dict[str, str]:
    """Return the fingerprints a pipeline-control proof must match."""
    return {
        "code": control_code_fingerprint(project_root),
        "fixtures": control_scenario_fingerprint(),
    }


def control_proof_registry(
    *, alpha_version: str = "1"
) -> tuple[StageRegistry, dict[str, FixtureStage]]:
    """Return preflight plus alpha/beta/gamma/omega with a bumpable alpha version."""
    preflight = PreflightStage()
    runners = {
        "alpha": FixtureStage("alpha"),
        "beta": FixtureStage("beta"),
        "gamma": FixtureStage("gamma"),
        "omega": FixtureStage("omega"),
    }
    estimate = ResourceEstimate()
    specs = (
        StageSpec("preflight", "1", (), (), (), estimate, (), (), preflight),
        StageSpec(
            "alpha",
            alpha_version,
            ("preflight",),
            ("preflight",),
            (),
            estimate,
            (),
            (),
            runners["alpha"],
        ),
        StageSpec("beta", "1", ("alpha",), ("alpha",), (), estimate, (), (), runners["beta"]),
        StageSpec("gamma", "1", ("beta",), ("beta",), (), estimate, (), (), runners["gamma"]),
        StageSpec("omega", "1", ("beta",), ("beta",), (), estimate, (), (), runners["omega"], True),
    )
    return StageRegistry(specs), runners
