"""Synthetic dbt artifacts for publication behavior tests."""

import json
from collections.abc import Sequence
from pathlib import Path

from arxiv_int.transformations.invoke import InvokeOutcome


def successful_invoke(args: Sequence[str], _credentials: object) -> InvokeOutcome:
    target = Path(args[args.index("--target-path") + 1])
    target.mkdir(parents=True, exist_ok=True)
    generation = json.loads(args[args.index("--vars") + 1])["generation_id"]
    nodes = {
        "model.fixture.docs": {
            "resource_type": "model",
            "schema": "derived",
            "name": "docs",
            "alias": f"docs__g_{generation}",
        },
        "test.fixture.docs": {
            "resource_type": "test",
            "depends_on": {"nodes": ["model.fixture.docs"]},
        },
    }
    (target / "manifest.json").write_text(
        json.dumps(
            {
                "metadata": {"invocation_id": "fixture"},
                "nodes": nodes,
            }
        )
    )
    (target / "run_results.json").write_text(
        json.dumps(
            {
                "metadata": {"invocation_id": "fixture"},
                "results": [
                    {"unique_id": "model.fixture.docs", "status": "success"},
                    {"unique_id": "test.fixture.docs", "status": "pass"},
                ],
            }
        )
    )
    return InvokeOutcome(True, "ok")
