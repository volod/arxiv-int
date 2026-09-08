"""Archive readability gate before forecast and stage work."""

import os

from arxiv_int.interfaces.pipeline import StageContext, StageResult
from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.interfaces.stores import DatasetRef
from arxiv_int.pipeline.run.context import RunContext
from arxiv_int.pipeline.run.errors import PreflightRefusedError


class PreflightStage:
    """Registered readability worker; does not load models or write archive bytes."""

    stage = "preflight"
    feature = "contracts"
    depends_on: tuple[str, ...] = ()

    def run(self, context: StageContext) -> StageResult:
        """Refuse unreadable silos and publish a path-free readability artifact."""
        _require_readable(context.silos)
        shard = context.options.get("document_id", "default")
        output = DatasetRef(self.stage, "1.0.0", context.generation_id, {"shard": shard})
        return StageResult(self.stage, "produced", "archive silos readable", outputs=(output,))


def preflight_run(context: RunContext) -> None:
    """Refuse unreadable archive silos; do not load models or write artifacts."""
    _require_readable(context.silos)


def _require_readable(silos: tuple[SiloRoot, ...]) -> None:
    for silo in silos:
        root = silo.root
        if not root.is_dir() or not os.access(root, os.R_OK):
            raise PreflightRefusedError(f"archive silo {silo.silo_id} is not readable")
