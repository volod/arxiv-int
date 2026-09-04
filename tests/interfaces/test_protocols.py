from collections.abc import Mapping, Sequence
from pathlib import Path

from arxiv_int.interfaces import (
    ArtifactStore,
    CanonicalStore,
    DatasetRef,
    DocumentExtractor,
    EmbeddingProfile,
    ExtractedDocument,
    GenerationRequest,
    GenerationResult,
    InferenceProvider,
    StageContext,
    StageResult,
    StageRunner,
    StoreStatus,
    TextEmbedder,
)


class FakeExtractor:
    name = "fake"
    feature = "extraction"

    def supports(self, media_type: str) -> bool:
        return media_type == "text/plain"

    def extract(self, source: Path) -> ExtractedDocument:
        return ExtractedDocument(text=source.name, media_type="text/plain", metadata={})


class FakeEmbedder:
    feature = "embeddings"
    profile = EmbeddingProfile(
        model_id="fake",
        revision="1",
        dimensions=2,
        pooling="mean",
        normalized=True,
        backend="fake",
    )

    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        return [[float(len(text)), 0.0] for text in texts]


class FakeProvider:
    name = "fake"
    feature = "inference"

    def available_models(self) -> Sequence[str]:
        return ["fake-model"]

    def generate(self, request: GenerationRequest) -> GenerationResult:
        return GenerationResult(
            text=request.prompt, status="ok", model_id="fake-model", model_digest="sha256:0"
        )


class FakeArtifactStore:
    feature = "lake"

    def locate(self, ref: DatasetRef) -> Path:
        return Path(ref.dataset)

    def publish(self, ref: DatasetRef, staged: Path) -> Path:
        return staged


class FakeCanonicalStore:
    feature = "store"

    def status(self) -> StoreStatus:
        return StoreStatus(available=False, detail="not configured")

    def schemas(self) -> Sequence[str]:
        return ["ctl", "corpus"]


class FakeStageRunner:
    stage = "inventory"
    feature = "lake"
    depends_on: tuple[str, ...] = ("preflight",)

    def run(self, context: StageContext) -> StageResult:
        return StageResult(stage=self.stage, outcome="completed", detail=context.run_id)


def test_backends_satisfy_their_protocols() -> None:
    assert isinstance(FakeExtractor(), DocumentExtractor)
    assert isinstance(FakeEmbedder(), TextEmbedder)
    assert isinstance(FakeProvider(), InferenceProvider)
    assert isinstance(FakeArtifactStore(), ArtifactStore)
    assert isinstance(FakeCanonicalStore(), CanonicalStore)
    assert isinstance(FakeStageRunner(), StageRunner)


def test_an_unrelated_object_does_not_satisfy_a_protocol() -> None:
    assert not isinstance(object(), DocumentExtractor)
    assert not isinstance(object(), StageRunner)


def test_extraction_result_keeps_backend_metadata() -> None:
    document = FakeExtractor().extract(Path("report.txt"))

    assert document.text == "report.txt"
    assert isinstance(document.metadata, Mapping)


def test_stage_result_reports_the_run_it_belongs_to() -> None:
    context = StageContext(
        stage="inventory",
        run_id="run-1",
        archive_dir=Path("/archive"),
        results_dir=Path("/results"),
        options={},
    )

    result = FakeStageRunner().run(context)

    assert result.outcome == "completed"
    assert result.detail == "run-1"
    assert result.outputs == ()


def test_dataset_reference_compares_by_value_and_carries_no_absolute_path() -> None:
    partition = {"bucket": "ab"}
    reference = DatasetRef(dataset="chunks", contract_version="1.0.0", partition=partition)

    assert reference == DatasetRef(dataset="chunks", contract_version="1.0.0", partition=partition)
    assert FakeArtifactStore().locate(reference) == Path("chunks")


def test_embedding_profile_identifies_comparable_vectors() -> None:
    embedder = FakeEmbedder()

    assert embedder.profile.dimensions == 2
    assert len(embedder.embed(["one", "two"])) == 2
