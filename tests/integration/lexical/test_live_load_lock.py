"""Declared live check that the load lock serializes loads but not the projection build."""

import os
import shutil
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from arxiv_int.pipeline.load_lexical.lock import LexicalLoadBusyError, exclusive_lexical_load
from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.stores.postgres.disposable import disposable_store, image_present
from arxiv_int.stores.postgres_image.pins import load_image_pins
from arxiv_int.stores.projections.database_lock import lock_projection_catalog

pytestmark = [
    pytest.mark.heavy,
    pytest.mark.skipif(shutil.which("docker") is None, reason="docker unavailable"),
    pytest.mark.skipif(
        os.environ.get("ARXIV_INT_RUN_LEXICAL") != "1",
        reason="set ARXIV_INT_RUN_LEXICAL=1 for the declared disposable lexical run",
    ),
]


def test_live_load_lock_refuses_a_second_load_and_frees_the_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = discover_project_root(Path(__file__))
    pins = load_image_pins(root)
    if not image_present(pins.local_image_ref):
        pytest.skip(f"image {pins.local_image_ref} is not present; build it first")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    with disposable_store(root, tmp_path / "pgdata-lock", pins=pins) as store:
        engine = create_engine(store.url)
        try:
            with exclusive_lexical_load(store.url):
                with pytest.raises(LexicalLoadBusyError), exclusive_lexical_load(store.url):
                    pytest.fail("a second load must not own the store")
                # The build takes the catalog lock from its own session meanwhile.
                with engine.begin() as connection:
                    lock_projection_catalog(connection)
            with (
                pytest.raises(RuntimeError, match="load failed"),
                exclusive_lexical_load(store.url),
            ):
                raise RuntimeError("load failed")
            with exclusive_lexical_load(store.url):
                pass
        finally:
            engine.dispose()
