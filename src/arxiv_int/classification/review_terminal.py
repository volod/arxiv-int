"""Interactive, fingerprint-bound operating-point review for a human operator."""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, TextIO

from arxiv_int.classification.artifacts import validate_manifest
from arxiv_int.classification.layout import ClassificationLayout, command_roots
from arxiv_int.classification.policy import load_classifier_policy
from arxiv_int.classification.vocabulary.policy import load_scheme_policy
from arxiv_int.classification.vocabulary.snapshot import check_snapshot, load_snapshot
from arxiv_int.classification.vocabulary.validate import errors
from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.run.persist import load_json

CHOICES = {"a": "accept", "r": "revise", "u": "retain-unclassified"}
THRESHOLDS = ("primary", "margin", "alternate")


def _say(output: TextIO, message: str = "") -> None:
    output.write(message + "\n")
    output.flush()


def _ask(input_stream: TextIO, output: TextIO, prompt: str) -> str:
    output.write(prompt)
    output.flush()
    answer = input_stream.readline()
    if not answer:
        raise ValueError("review stopped at end of input; no decision recorded")
    return answer.strip()


def _packet(layout: ClassificationLayout, project_root: Path) -> tuple[dict[str, Any], str]:
    path = layout.review / "operating-point.json"
    packet = load_json(path)
    mapping = packet.get("mappingManifest")
    if not isinstance(mapping, dict):
        raise ValueError("operating-point packet has no sealed mapping")
    manifest = Path(str(mapping["path"]))
    validate_manifest(manifest, str(mapping["sha256"]))
    if errors(check_snapshot(layout.scheme, load_scheme_policy(project_root))):
        raise ValueError("scheme snapshot is stale or damaged; create a fresh run")
    scheme = load_snapshot(layout.scheme)
    if packet.get("schemeId") != scheme.manifest["schemeId"]:
        raise ValueError("packet scheme identity does not match the sealed scheme")
    policy = load_classifier_policy(project_root)
    if packet.get("classifier", {}).get("configuration_sha256") != policy.sha256:
        raise ValueError("packet classifier policy is stale; create a fresh run")
    integrity = packet.get("integrity")
    if (
        isinstance(integrity, dict)
        and hash_file(Path(str(integrity["log"])))[0] != integrity["sha256"]
    ):
        raise ValueError("archive integrity report checksum changed")
    evaluation = packet.get("evaluation")
    if isinstance(evaluation, dict):
        report_path = Path(str(evaluation["metrics"]))
        if hash_file(report_path)[0] != evaluation["sha256"]:
            raise ValueError("held-out evaluation checksum changed")
        report = load_json(report_path)
        expected_mapping = {"manifest": mapping["path"], "sha256": mapping["sha256"]}
        if report.get("classification") != expected_mapping or report.get(
            "passed"
        ) != evaluation.get("passed"):
            raise ValueError("held-out evaluation does not match this mapping and verdict")
    return packet, hash_file(path)[0]


def _show_packet(packet: dict[str, Any], layout: ClassificationLayout, output: TextIO) -> None:
    _say(output, f"Run review: {packet['humanTask']}")
    _say(output, f"Scheme: {packet['schemeId']}  Readiness: {packet['readiness']}")
    _say(output, f"Mapping SHA-256: {packet['mappingManifest']['sha256']}")
    _say(output, f"Classification counts: {packet['countsByPrimary']}")
    _say(output, f"Current thresholds: {packet['classifier']['thresholds']}")
    _say(output, f"Exceptional outcomes: {json.dumps(packet.get('outcomes'), ensure_ascii=False)}")
    _say(output, f"Pending: {', '.join(packet.get('pending', [])) or 'none'}")
    scheme = load_snapshot(layout.scheme).scheme
    _say(output, "\nDomain captions (English | Russian | Ukrainian):")
    for identity in scheme.children(None):
        if not identity.startswith("tax:"):
            continue
        item = scheme.classes[identity]
        _say(
            output, f"{identity}: " + " | ".join(f"{lang}: {text}" for lang, text in item.captions)
        )
    evaluation = packet.get("evaluation")
    if isinstance(evaluation, dict):
        report = load_json(Path(str(evaluation["metrics"])))
        _say(output, f"Held-out gates: {'pass' if report['passed'] else 'fail'}")
        _say(output, f"Metrics: {json.dumps(report['metrics'], ensure_ascii=False)}")
    for name, examples in packet.get("inspectionCases", packet.get("reviewSamples", {})).items():
        _say(output, f"\n{name} examples:")
        for example in examples:
            _say(
                output,
                f"- {example.get('relativePath', '[unknown path]')}: "
                f"{example.get('primaryProposal', example.get('primary'))}, "
                f"confidence {example.get('confidence', '[unknown]')}",
            )
            evidence = example.get("evidence", [])
            if evidence:
                _say(
                    output,
                    "  Evidence: "
                    + ", ".join(
                        str(item.get("term", "")) for item in evidence if isinstance(item, dict)
                    ),
                )
            if example.get("failureReason"):
                _say(output, f"  Reason: {example['failureReason']}")


def _can_accept(packet: dict[str, Any]) -> bool:
    evaluation = packet.get("evaluation")
    calibration = packet.get("calibration")
    return (
        packet.get("readiness") == "ready"
        and not packet.get("pending")
        and isinstance(packet.get("integrity"), dict)
        and isinstance(evaluation, dict)
        and evaluation.get("passed") is True
        and isinstance(calibration, dict)
        and calibration.get("qualityGatesPassed") is True
        and calibration.get("reportSha256") == evaluation.get("sha256")
    )


def _revisions(input_stream: TextIO, output: TextIO, packet: dict[str, Any]) -> dict[str, Any]:
    proposed: dict[str, float] = {}
    current = packet["classifier"]["thresholds"]
    for field in THRESHOLDS:
        prior = current.get(field)
        while True:
            raw = _ask(input_stream, output, f"{field} (0..1; Enter keeps {prior}): ")
            if not raw:
                break
            try:
                value = float(raw)
            except ValueError:
                _say(output, "Enter a number between 0 and 1.")
                continue
            if 0.0 <= value <= 1.0:
                proposed[field] = value
                break
            _say(output, "Enter a number between 0 and 1.")
    exceptions = _ask(
        input_stream,
        output,
        "Describe proposed unclassified/unreadable handling (required): ",
    )
    if not exceptions:
        raise ValueError("revision needs a description of exceptional-outcome handling")
    return {"thresholds": proposed, "exceptionalOutcomes": exceptions}


def _write_exclusive(path: Path, document: dict[str, Any]) -> None:
    payload = json.dumps(document, sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\n"
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="ascii", dir=path.parent, prefix=".decision-", delete=False
        ) as handle:
            temporary = Path(handle.name)
            os.chmod(temporary, 0o600)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def review_operating_point(
    project_root: Path,
    runs_dir: Path,
    run_id: str,
    input_stream: TextIO,
    output: TextIO,
) -> int:
    """Present decoded evidence and record one explicit human decision, never policy edits."""
    layout = ClassificationLayout.for_run(runs_dir, run_id)
    packet, packet_digest = _packet(layout, project_root)
    destination = layout.review / "decision.json"
    if destination.exists():
        raise ValueError(f"decision already exists: {destination}; it will not be overwritten")
    _show_packet(packet, layout, output)
    _say(output, "\nAccept is available only after passing held-out calibration.")
    choice = _ask(
        input_stream, output, "[a]ccept, [r]evise, retain-[u]nclassified, [q]uit: "
    ).lower()
    if choice == "q":
        _say(output, "No decision recorded.")
        return 0
    if choice not in CHOICES:
        raise ValueError("choose a, r, u, or q")
    if choice == "a" and not _can_accept(packet):
        raise ValueError("accept refused: reviewed held-out calibration is not ready and passing")
    proposal = _revisions(input_stream, output, packet) if choice == "r" else None
    note = _ask(input_stream, output, "Review rationale (required): ")
    if not note:
        raise ValueError("decision rationale is required")
    confirmation = _ask(input_stream, output, f"Type {CHOICES[choice]} to record decision: ")
    if confirmation != CHOICES[choice]:
        _say(output, "No decision recorded.")
        return 0
    evaluation = packet.get("evaluation")
    document = {
        "schema": "arxiv-int.classification-operating-decision.v1",
        "humanTask": "approve-classification-operating-point",
        "runId": run_id,
        "decision": CHOICES[choice],
        "approvalStatus": "approved" if choice == "a" else "not-approved",
        "packetReadiness": packet["readiness"],
        "rationale": note,
        "proposal": proposal,
        "packetSha256": packet_digest,
        "mappingManifest": packet["mappingManifest"],
        "scheme": packet["scheme"],
        "classifier": packet["classifier"],
        "evaluation": evaluation,
    }
    _write_exclusive(destination, document)
    _say(output, f"Decision recorded: {destination}")
    _say(output, "This does not edit policy or authorize archive placement.")
    return 0


def run_review(args: Any) -> int:
    """CLI adapter requiring an actual terminal for human decisions."""
    if not sys.stdin.isatty():
        raise ValueError("interactive review needs a terminal")
    root, runs_dir = command_roots(args)
    return review_operating_point(root, runs_dir, str(args.run_id), sys.stdin, sys.stdout)
