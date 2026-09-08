"""Declared investigation and lexical profiles aligned with setup's stage seam."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from arxiv_int.contracts.generate.normalize import normalize_json
from arxiv_int.pipeline.publish.model import PROFILE_SCHEMA, OutputFamily, PipelineProfile
from arxiv_int.pipeline.stages import OPTIONAL_STAGES
from arxiv_int.runtime.setup.requirements import PROFILE_STAGES

PIPELINE_DIR = Path("configs") / "pipeline"


def _family(family_id: str, stage: str, required: bool, path: str = "") -> OutputFamily:
    return OutputFamily(family_id, stage, required, path)


INVESTIGATION_FAMILIES: tuple[OutputFamily, ...] = (
    _family("inventory", "inventory", True),
    _family("documents", "chunk", True),
    _family("classification", "classify", True),
    _family("lexical", "load-lexical", True),
    _family("topics", "topics", True),
    _family("identities", "entities", True),
    _family("ontology", "ontology", True),
    _family("facts", "facts", True),
    _family("domain", "domain-artifacts", True),
    _family("evaluation", "evaluate", True),
    _family("anomalies", "evaluate", True),
    _family("report", "report", True, "reports/index.html"),
    _family("vectors", "load-vector", False),
    _family("graph", "graph", False),
)

LEXICAL_FAMILIES: tuple[OutputFamily, ...] = (
    _family("inventory", "inventory", True),
    _family("documents", "chunk", True),
    _family("classification", "classify", True),
    _family("lexical", "load-lexical", True),
    _family("evaluation", "evaluate", True),
    _family("report", "report", True, "reports/index.html"),
)

DEFAULT_PROFILES: dict[str, PipelineProfile] = {
    "investigation": PipelineProfile(
        "investigation",
        PROFILE_STAGES["investigation"],
        tuple(sorted(OPTIONAL_STAGES)),
        INVESTIGATION_FAMILIES,
    ),
    "lexical": PipelineProfile(
        "lexical",
        PROFILE_STAGES["lexical"],
        (),
        LEXICAL_FAMILIES,
    ),
}

FIXTURE_PROFILE = PipelineProfile(
    "fixture",
    ("alpha", "beta", "gamma"),
    ("omega",),
    (
        _family("alpha", "alpha", True),
        _family("beta", "beta", True),
        _family("gamma", "gamma", True, "reports/index.html"),
        _family("omega", "omega", False),
    ),
    report_family="gamma",
)


def profile_payload(profile: PipelineProfile) -> dict[str, Any]:
    """Serialize one profile for the committed config file."""
    return {
        "families": [
            {
                "id": item.family_id,
                "path": item.path,
                "required": item.required,
                "stage": item.stage,
            }
            for item in profile.families
        ],
        "name": profile.name,
        "optional_stages": list(profile.optional_stages),
        "report_family": profile.report_family,
        "required_stages": list(profile.required_stages),
        "schema": PROFILE_SCHEMA,
    }


def profile_from_payload(payload: Mapping[str, Any]) -> PipelineProfile:
    """Build a profile from a JSON object."""
    families = tuple(
        OutputFamily(
            str(item["id"]),
            str(item["stage"]),
            bool(item.get("required", True)),
            str(item.get("path", "")),
        )
        for item in payload.get("families", ())
        if isinstance(item, dict)
    )
    return PipelineProfile(
        str(payload["name"]),
        tuple(str(name) for name in payload.get("required_stages", ())),
        tuple(str(name) for name in payload.get("optional_stages", ())),
        families,
        str(payload.get("report_family", "report")),
    )


def load_profile(name: str, project_root: Path | None = None) -> PipelineProfile:
    """Load a named profile from configs, then defaults, then the fixture profile."""
    if project_root is not None:
        path = project_root / PIPELINE_DIR / f"{name}.json"
        if path.is_file():
            return profile_from_payload(_read_object(path))
    if name in DEFAULT_PROFILES:
        return DEFAULT_PROFILES[name]
    if name == FIXTURE_PROFILE.name:
        return FIXTURE_PROFILE
    known = ", ".join(sorted(DEFAULT_PROFILES))
    raise ValueError(f"unknown pipeline profile {name!r}; expected {known}")


def write_profile(project_root: Path, profile: PipelineProfile) -> Path:
    """Write one committed profile overlay."""
    directory = project_root / PIPELINE_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{profile.name}.json"
    path.write_text(normalize_json(profile_payload(profile)), encoding="utf-8")
    return path


def check_profile_alignment() -> tuple[str, ...]:
    """Return findings when committed defaults drift from setup PROFILE_STAGES."""
    findings: list[str] = []
    for name, stages in PROFILE_STAGES.items():
        findings.extend(_one_profile_findings(name, stages))
    findings.extend(_lexical_subset_findings())
    return tuple(findings)


def _one_profile_findings(name: str, stages: tuple[str, ...]) -> tuple[str, ...]:
    declared = DEFAULT_PROFILES.get(name)
    if declared is None:
        return (f"setup profile {name} has no pipeline output declaration",)
    notes: list[str] = []
    if declared.required_stages != stages:
        notes.append(f"profile {name} required_stages drifted from PROFILE_STAGES")
    optional = set(declared.optional_stages)
    if name == "investigation" and optional != set(OPTIONAL_STAGES):
        notes.append("investigation optional_stages drifted from OPTIONAL_STAGES")
    if name == "lexical" and optional:
        notes.append("lexical profile must not declare optional GPU/graph stages")
    required_ids = {item.family_id for item in declared.families if item.required}
    if "report" not in required_ids:
        notes.append(f"profile {name} is missing a required report family")
    return tuple(notes)


def _lexical_subset_findings() -> tuple[str, ...]:
    investigation = DEFAULT_PROFILES["investigation"]
    lexical = DEFAULT_PROFILES["lexical"]
    notes: list[str] = []
    if len(lexical.required_stages) >= len(investigation.required_stages):
        notes.append("lexical profile is not smaller than investigation")
    lex_req = sum(1 for item in lexical.families if item.required)
    inv_req = sum(1 for item in investigation.families if item.required)
    if lex_req >= inv_req:
        notes.append("lexical required families are not a smaller investigation subset")
    return tuple(notes)


def _read_object(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} is not a JSON object")
    return loaded
