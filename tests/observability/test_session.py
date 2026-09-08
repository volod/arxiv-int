"""Stage sessions write JSONL, console logs, and a final manifest."""

import json
import logging
from pathlib import Path

from arxiv_int.inference.telemetry import TelemetrySink
from arxiv_int.observability.constants import SCHEMA_ID
from arxiv_int.observability.resources import FixedResourceSampler
from arxiv_int.observability.session import StageSession


def test_stage_session_writes_jsonl_console_and_manifest(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "run-1"
    logger = logging.getLogger("tests.observability.session")
    sampler = FixedResourceSampler()
    with StageSession(
        run_dir,
        "run-1",
        "extract",
        shard="document-identifier-long",
        logger=logger,
        sampler=sampler,
        clock=lambda: 10.0,
        stamp=lambda: "2026-09-07T00:00:00Z",
        interval_sec=1.0,
        log_format="console+jsonl",
        extra_secrets=("hunter2",),
        telemetry=TelemetrySink(run_dir / "telemetry" / "resource-events.jsonl"),
    ) as session:
        logger.info("password=hunter2 prompt=secret-document-body")
        session.progress(processed=3, remaining=7, bytes_delta=128, force=True)
    logs = run_dir / "logs"
    console = (logs / "console.log").read_text(encoding="utf-8")
    events = (logs / "events.jsonl").read_text(encoding="utf-8")
    progress = (logs / "progress.jsonl").read_text(encoding="utf-8")
    manifest = json.loads((logs / "observability-manifest.json").read_text(encoding="utf-8"))
    assert "hunter2" not in console
    assert "secret-document-body" not in events
    assert "password=<redacted>" in events or "password=<redacted>" in console
    assert SCHEMA_ID in progress
    assert "document-identifier-long" not in progress
    rows = [json.loads(line) for line in progress.splitlines() if line]
    assert rows[0]["event"] == "stage-start"
    assert rows[-1]["event"] == "stage-complete"
    assert rows[-1]["worker_state"] == "completed"
    assert manifest["schema"] == SCHEMA_ID
    assert manifest["outcome"] == "produced"
    telemetry = (run_dir / "telemetry" / "resource-events.jsonl").read_text(encoding="utf-8")
    assert "pipeline.resource" in telemetry
    assert "prompt" not in telemetry


def test_heartbeat_pump_ticks_until_stop() -> None:
    import threading

    from arxiv_int.observability.pump import HeartbeatPump

    hits: list[int] = []
    gate = threading.Event()

    def tick() -> None:
        hits.append(1)
        gate.set()

    pump = HeartbeatPump(tick, 0.05)
    pump.start()
    assert gate.wait(2.0)
    pump.stop()
    assert hits
