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
    SiloRoot,
    SourceOccurrence,
    StageContext,
    StageResult,
    StageRunner,
    StoreStatus,
    TextEmbedder,
    TransformationRunRef,
    ValidationResultRef,
)


class FakeExtractor:
    name = "fake"
    feature = "extraction"

    def supports(self, media_type: str) -> bool:
        return media_type == "text/plain"

    def extract(self, source: Path, occurrence: SourceOccurrence) -> ExtractedDocument:
        return ExtractedDocument(
            text=source.name,
            media_type="text/plain",
            occurrence=occurrence,
            extractor_profile=self.name,
        )


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
        return Path(ref.dataset) / ref.generation_id

    def publish(self, ref: DatasetRef, staged: Path) -> Path:
        return staged / ref.generation_id


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
        return StageResult(
            stage=self.stage,
            outcome="produced",
            detail=context.generation_id,
            outputs=(
                DatasetRef(
                    dataset="source-occurrences",
                    contract_version="1.0.0",
                    generation_id=context.generation_id,
                    partition={"scan_id": context.run_id},
                ),
            ),
            validations=(
                ValidationResultRef(
                    contract_id="urn:arxiv-int:contract:source-occurrences:1.0.0",
                    generation_id=context.generation_id,
                    catalog_fingerprint="sha256:catalog",
                    status="pass",
                    publishable=True,
                ),
            ),
            transformations=(
                TransformationRunRef(
                    run_id=context.run_id,
                    generation_id=context.generation_id,
                    command="parse",
                    status="not-run",
                    input_fingerprint="sha256:input",
                    model_fingerprint="sha256:model",
                    activatable=False,
                ),
            ),
        )


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


def test_extraction_result_keeps_backend_metadata_and_occurrence() -> None:
    occurrence = SourceOccurrence(silo_id="alpha", relative_path="report.txt", scan_id="scan-1")
    document = FakeExtractor().extract(Path("report.txt"), occurrence)

    assert document.text == "report.txt"
    assert document.occurrence == occurrence
    assert isinstance(document.metadata, Mapping)


def test_stage_result_reports_the_generation_it_belongs_to() -> None:
    context = StageContext(
        stage="inventory",
        run_id="run-1",
        generation_id="gen-1",
        silos=(SiloRoot("alpha", Path("/archive-alpha")),),
        results_dir=Path("/results"),
        options={},
    )

    result = FakeStageRunner().run(context)

    assert result.outcome == "produced"
    assert result.detail == "gen-1"
    assert result.outputs[0].generation_id == "gen-1"
    assert result.validations[0].publishable is True
    assert result.transformations[0].activatable is False


def test_embedding_profile_identifies_comparable_vectors() -> None:
    embedder = FakeEmbedder()

    assert embedder.profile.dimensions == 2
    assert len(embedder.embed(["one", "two"])) == 2


def test_generation_result_reports_only_successful_timed_throughput() -> None:
    success = GenerationResult(
        text="ok",
        status="ok",
        model_id="model",
        model_digest="sha256:model",
        completion_tokens=20,
        latency_seconds=2.0,
    )
    failed = GenerationResult(
        text="",
        status="timeout",
        model_id="model",
        model_digest="sha256:model",
        completion_tokens=20,
        latency_seconds=2.0,
    )

    assert success.tokens_per_second == 10.0
    assert failed.tokens_per_second == 0.0
