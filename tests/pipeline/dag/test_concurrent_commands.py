"""Separate commands serialize cache writes and skip duplicate fixture work."""

import subprocess
import sys
from pathlib import Path

from arxiv_int.pipeline.run.persist import load_status
from arxiv_int.pipeline.run.reuse_index import load_reuse_index
from tests.pipeline.conftest import make_context

_SCRIPT = """
import sys
from pathlib import Path
from arxiv_int.pipeline.run.fixtures import fixture_registry
from arxiv_int.pipeline.dag.orchestrate import Orchestrator
from arxiv_int.pipeline.run.persist import load_context
from tests.pipeline.publish.test_publish import _plan
runs, run_id, calls = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
context = load_context(runs, run_id)
registry, runners = fixture_registry()
def hook(context):
    with calls.open('a') as handle:
        handle.write(context.stage + '\\n')
for runner in runners.values():
    runner._hook = hook
status = Orchestrator(registry, runs).execute_plan(context, _plan(registry))
assert not status.halted
"""


def test_concurrent_commands_do_not_duplicate_workers(tmp_path: Path) -> None:
    context = make_context(tmp_path)
    calls = tmp_path / "calls.txt"
    command = [sys.executable, "-c", _SCRIPT, str(context.runs_dir), context.run_id, str(calls)]
    processes = [
        subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)
    ]
    try:
        for process in processes:
            _stdout, stderr = process.communicate(timeout=30)
            assert process.returncode == 0, stderr.decode()
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
    assert calls.read_text().splitlines() == ["alpha", "beta", "gamma"]
    assert len(load_reuse_index(context.runs_dir)) == 3
    assert all(item.cache_hit for item in load_status(context.runs_dir, context.run_id).executions)
