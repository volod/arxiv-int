from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from arxiv_int.evaluation.bundles import publish_run_bundle, verify_run_bundle
from arxiv_int.evaluation.bundles.errors import BundleExistsError
from tests.evaluation.bundles.bundle_support import spec


def test_competing_publishers_leave_one_immutable_bundle(tmp_path: Path) -> None:
    target = tmp_path / "run-1"
    start = Barrier(2)
    results: list[object] = []

    def _publish(marker: str) -> None:
        start.wait(timeout=5)
        try:
            results.append(publish_run_bundle(target, spec(), [{"marker": marker}]))
        except BundleExistsError as error:
            results.append(error)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(_publish, "a")
        second = pool.submit(_publish, "b")
        first.result(timeout=10)
        second.result(timeout=10)

    published = [item for item in results if not isinstance(item, BundleExistsError)]
    refused = [item for item in results if isinstance(item, BundleExistsError)]
    assert len(published) == 1
    assert len(refused) == 1
    fingerprint = verify_run_bundle(target)
    assert published[0].fingerprint == fingerprint
    assert not list(tmp_path.glob(".run-1.tmp-*"))
