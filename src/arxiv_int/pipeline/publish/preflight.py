"""Archive readability gate before forecast and stage work."""

import os

from arxiv_int.pipeline.context import RunContext
from arxiv_int.pipeline.errors import PreflightRefusedError


def preflight_run(context: RunContext) -> None:
    """Refuse unreadable archive silos; do not load models or write artifacts."""
    for silo in context.silos:
        root = silo.root
        if not root.is_dir() or not os.access(root, os.R_OK):
            raise PreflightRefusedError(f"archive silo {silo.silo_id} is not readable: {root}")
