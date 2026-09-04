"""Prove the core import graph never reaches an optional feature group."""

import subprocess
import sys

from arxiv_int.features import optional_modules

_PROBE = "\n".join(
    (
        "import sys",
        "import arxiv_int",
        "import arxiv_int.cli",
        "import arxiv_int.config",
        "import arxiv_int.doctor",
        "import arxiv_int.features",
        "import arxiv_int.inference",
        "import arxiv_int.interfaces",
        "import arxiv_int.observability",
        "import arxiv_int.paths",
        "import arxiv_int.pipeline",
        "import arxiv_int.quality.plan_summary",
        "print('\\n'.join(sorted(sys.modules)))",
    )
)


def _imported_modules() -> set[str]:
    completed = subprocess.run(
        [sys.executable, "-c", _PROBE], capture_output=True, text=True, check=True
    )
    return set(completed.stdout.split())


def test_core_import_pulls_no_optional_module() -> None:
    loaded = _imported_modules()

    assert "arxiv_int.interfaces" in loaded
    assert optional_modules().isdisjoint(loaded)
    assert not any(name == "selfsuvis" or name.startswith("selfsuvis.") for name in loaded)
    assert {"torch", "dotenv", "qdrant_client"}.isdisjoint(loaded)
