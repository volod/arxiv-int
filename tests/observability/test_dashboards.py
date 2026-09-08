"""Provisioned Grafana dashboards stay secret-free with bounded query labels."""

import json
from pathlib import Path

from arxiv_int.observability.constants import FORBIDDEN_LABEL_NAMES
from arxiv_int.quality.project_root import discover_project_root

DASHBOARD_DIR = discover_project_root(Path(__file__)) / "docker" / "grafana" / "dashboards"


def test_pipeline_dashboards_exist_and_avoid_high_cardinality_labels() -> None:
    files = list(DASHBOARD_DIR.glob("*.json"))
    names = {path.name for path in files}
    assert "pipeline-progress.json" in names
    assert "resource-pressure.json" in names
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        text = json.dumps(payload)
        assert "POSTGRES_PASSWORD" not in text
        assert "prompt" not in text.lower()
        assert payload["editable"] is False
        assert payload["uid"]
        for name in FORBIDDEN_LABEL_NAMES:
            assert f'legendFormat": "{{{{{name}}}}}' not in text
        for panel in payload["panels"]:
            assert panel["datasource"]["uid"] == "arxiv-int-postgres"
            sql = panel["targets"][0]["rawSql"]
            assert "ctl.stage_progress" in sql
            assert "document_id" not in sql
