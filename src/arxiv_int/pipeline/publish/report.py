"""Diagnostic report rendering; writing a report cannot activate a generation."""

from pathlib import Path

from arxiv_int.pipeline.publish.model import REPORT_HTML, REPORT_JSON, KnowledgeBase
from arxiv_int.pipeline.run.persist import run_dir, write_json


def write_report(runs_dir: Path, document: KnowledgeBase) -> Path:
    """Write ASCII HTML and JSON diagnostics under the run; do not switch pointers."""
    root = run_dir(runs_dir, document.run_id)
    html_path = root / REPORT_HTML
    json_path = root / REPORT_JSON
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(_html(document), encoding="utf-8")
    write_json(
        json_path,
        {
            "generation_id": document.generation_id,
            "limitations": list(document.limitations),
            "profile": document.profile,
            "report_path": REPORT_HTML,
            "resume_command": document.resume_command,
            "run_id": document.run_id,
            "status": document.status,
            "status_command": document.status_command,
        },
    )
    return html_path


def _html(document: KnowledgeBase) -> str:
    lines = [
        "<!DOCTYPE html>",
        '<html lang="en"><head><meta charset="utf-8">',
        f"<title>run {document.run_id}</title></head><body>",
        f"<h1>knowledge-base {document.run_id}</h1>",
        f"<p>profile={document.profile} status={document.status}</p>",
        f"<p>generation={document.generation_id} active={str(document.active).lower()}</p>",
        f"<p>{document.status_command}</p>",
        f"<p>{document.resume_command}</p>",
        "<ul>",
    ]
    for item in document.outputs:
        lines.append(f"<li>{item.family} stage={item.stage} outcome={item.outcome}</li>")
    lines.append("</ul></body></html>")
    lines.append("")
    return "\n".join(lines)
