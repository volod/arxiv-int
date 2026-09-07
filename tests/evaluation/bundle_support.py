from arxiv_int.evaluation.bundles import BundleSpec


def spec() -> BundleSpec:
    return BundleSpec(
        run_id="run-1",
        kind="retrieval",
        input_fingerprints={"gold": "sha256:abc"},
        configuration={"k": 5},
        metrics={"recall_at_k": 1.0},
        verdict="adopt",
    )
