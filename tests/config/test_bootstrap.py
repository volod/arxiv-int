"""Shell bootstrap behavior for the checkout dotenv file."""

import subprocess
from pathlib import Path


def _sync_dotenv(root: Path) -> subprocess.CompletedProcess[str]:
    script = Path(__file__).parents[2] / "scripts/shared/common.sh"
    return subprocess.run(
        ["bash", "-c", 'source "$1"; arxiv_int_sync_dotenv', "bash", str(script)],
        check=True,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "PROJECT_ROOT": str(root)},
    )


def test_shell_bootstrap_creates_dotenv_from_template(tmp_path: Path) -> None:
    root = tmp_path / "checkout"
    root.mkdir()
    example = "ARCHIVE_DIR=/archive\n# POSTGRES_PASSWORD=\nDATA_DIR=.data\n"
    (root / ".env.example").write_text(example, encoding="utf-8")

    completed = _sync_dotenv(root)

    assert completed.stdout == "Created .env from .env.example\n"
    assert (root / ".env").read_text(encoding="utf-8") == example


def test_shell_bootstrap_appends_only_missing_dotenv_declarations(tmp_path: Path) -> None:
    root = tmp_path / "checkout"
    root.mkdir()
    (root / ".env.example").write_text(
        "KEEP=template\nNEW=active\n# SECRET=\n# OPTIONAL=\n", encoding="utf-8"
    )
    (root / ".env").write_text("KEEP=operator\n# SECRET=\n", encoding="utf-8")

    first = _sync_dotenv(root)
    second = _sync_dotenv(root)
    result = (root / ".env").read_text(encoding="utf-8")

    assert first.stdout == "Added 2 missing variable declaration(s) to .env\n"
    assert second.stdout == ""
    assert "KEEP=operator" in result
    assert "KEEP=template" not in result
    assert result.count("NEW=active") == 1
    assert result.count("# OPTIONAL=") == 1


def test_make_bootstrap_finishes_through_the_readiness_target() -> None:
    root = Path(__file__).parents[2]

    completed = subprocess.run(
        ["make", "--no-print-directory", "--dry-run", "bootstrap"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "arxiv_int_sync_dotenv" in completed.stdout
    assert "package-check" in completed.stdout
    assert "readiness READINESS_ALLOW_DEGRADED=1" in completed.stdout
