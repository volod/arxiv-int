"""Compose image listing and offline pull policy."""

from pathlib import Path

from arxiv_int.runtime.setup.images import (
    compose_service_images,
    run_images_phase,
    run_postgres_image_phase,
)
from tests.compose.test_profiles import _runtime_config
from tests.runtime.setup.conftest import PROJECT_ROOT, checkout, completed


def test_compose_service_images_skip_local_postgres() -> None:
    images = compose_service_images(PROJECT_ROOT)
    assert "database" in images
    assert images["database"].startswith("arxiv-int/postgres")
    assert "grafana" in images
    assert "@sha256:" in images["grafana"]


def test_offline_images_refuse_cache_miss(tmp_path: Path) -> None:
    config = _runtime_config(tmp_path)
    result = run_images_phase(
        config,
        "pipeline",
        downloads=False,
        runner=lambda *_a, **_k: completed(0),
        image_present=lambda _ref: False,
        listed_images={"grafana": "grafana/grafana:fixture"},
    )
    assert result.status == "blocked"
    assert "offline" in result.detail


def test_postgres_image_reuses_present_ref(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    result = run_postgres_image_phase(
        PROJECT_ROOT,
        downloads=False,
        image_present=lambda _ref: True,
        builder=lambda _root: 1,
        verified={},
    )
    assert result.status == "ready"
    del root
