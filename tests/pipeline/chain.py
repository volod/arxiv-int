"""Run inventory, extraction, normalization, grouping, and chunking in one chain."""

from dataclasses import dataclass, replace
from pathlib import Path
from typing import cast

from arxiv_int.extraction.model import ExtractionError, ExtractionPolicy
from arxiv_int.extraction.router import TieredExtractor
from arxiv_int.extraction.stage import ExtractionStage
from arxiv_int.interfaces.extraction import DocumentExtractor, ExtractedDocument
from arxiv_int.interfaces.pipeline import StageContext, StageResult
from arxiv_int.interfaces.sources import SiloRoot, SourceAnchor, SourceOccurrence
from arxiv_int.pipeline.chunk.model import ChunkPolicy
from arxiv_int.pipeline.chunk.stage import ChunkStage
from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.dedupe.model import DedupePolicy
from arxiv_int.pipeline.dedupe.stage import DedupeStage
from arxiv_int.pipeline.inventory.stage import InventoryStage
from arxiv_int.pipeline.normalize.model import NormalizePolicy
from arxiv_int.pipeline.normalize.stage import NormalizeStage

TABLE_DOCUMENT = (
    "OTCHET 2024\n"
    "\n"
    "| Item | Amount |\n"
    "| --- | --- |\n"
    "| Bolt | 100 kg |\n"
    "| Nut | 200 kg |\n"
    "| Washer | 300 kg |\n"
    "\n"
    "1. Vvedenie\n"
    "\n"
    "Postavka vypolnena v srok. Priemka provedena komissiej. "
    "Zamechanij po kachestvu net.\n"
)
PROSE_DOCUMENT = (
    "\ufeffDogovor 42\r\n"
    "\r\n"
    "Storony soglasovali objem postavki. "
    "Cena zafiksirovana v prilozhenii. "
    "Srok dejstviya prodlen.\r\n"
)
COPY_DOCUMENT = PROSE_DOCUMENT.replace("\r\n", "\n").replace("\ufeff", "")
LONG_DOCUMENT = (
    "\n\n".join(
        f"Punkt {index}. Postavshchik obespechivaet kachestvo tovara "
        f"i soblyudaet srok postavki nomer {index}."
        for index in range(1, 41)
    )
    + "\n"
)
NEAR_DOCUMENT = LONG_DOCUMENT.replace("Punkt 7. Postavshchik", "Punkt 7. Novyj postavshchik")


def _edition(text: str) -> str:
    """Rewrite every third clause so the result stays an edition, not a duplicate."""
    for index in range(1, 41, 3):
        text = text.replace(
            f"Punkt {index}. Postavshchik obespechivaet kachestvo tovara",
            f"Punkt {index}. Ispolnitel garantiruet nadlezhashchee sostoyanie gruza",
        )
    return text


EDITION_DOCUMENT = _edition(LONG_DOCUMENT)
RUSSIAN_DOCUMENT = (
    "\u0414\u043e\u0433\u043e\u0432\u043e\u0440 \u043f\u043e\u0441\u0442\u0430\u0432\u043a\u0438\n"
    "\n"
    "\u041e\u0431\u0449\u0435\u0441\u0442\u0432\u043e \u0441 "
    "\u043e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d\u043d\u043e\u0439 "
    "\u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0435\u043d\u043d\u043e\u0441\u0442\u044c"
    "\u044e \u043f\u0435\u0440\u0435\u0434\u0430\u043b\u043e "
    "\u0442\u043e\u0432\u0430\u0440 \u043d\u0430 \u0441\u043a\u043b\u0430\u0434. "
    "\u0410\u043a\u0442 \u043f\u043e\u0434\u043f\u0438\u0441\u0430\u043d "
    "\u0431\u0435\u0437 \u0437\u0430\u043c\u0435\u0447\u0430\u043d\u0438\u0439.\n"
)

FIXTURES: dict[str, str] = {
    "table.txt": TABLE_DOCUMENT,
    "prose.txt": PROSE_DOCUMENT,
    "copy.txt": COPY_DOCUMENT,
    "long.txt": LONG_DOCUMENT,
    "near.txt": NEAR_DOCUMENT,
    "edition.txt": EDITION_DOCUMENT,
    "russian.txt": RUSSIAN_DOCUMENT,
    "blank.txt": "\u200b\u200b\n",
}


@dataclass(frozen=True, slots=True)
class ChainRun:
    """Every stage result produced by one fixture corpus chain."""

    context: StageContext
    inventory: StageResult
    extract: StageResult
    normalize: StageResult
    dedupe: StageResult
    chunk: StageResult

    def manifest(self, result: StageResult) -> Path:
        """Return the published manifest path of one stage result."""
        return Path(result.outputs[0].partition["manifest"])


class ChainRouter:
    """Return fixture text with one whole-document anchor and no tool calls."""

    def extract(
        self,
        source: Path,
        occurrence: SourceOccurrence,
        media_type: str,
        encoding: str | None,
    ) -> ExtractedDocument:
        """Decode fixture bytes, refusing content the fixtures mark as corrupt."""
        text = source.read_bytes().decode(encoding or "utf-8")
        if "corrupt" in text:
            raise ExtractionError("parser-corrupt", "fixture parser rejected corrupt content")
        anchor = SourceAnchor(occurrence, start_char=0, end_char=len(text), page=1, kind="text")
        return ExtractedDocument(
            text, media_type, occurrence, "fixture", (anchor,), {"tool_version": "fixture-1"}
        )


def run_chain(
    tmp_path: Path,
    *,
    fixtures: dict[str, str] | None = None,
    raw_fixtures: dict[str, bytes] | None = None,
    router: DocumentExtractor | None = None,
    chunk_policy: ChunkPolicy | None = None,
    dedupe_policy: DedupePolicy | None = None,
) -> ChainRun:
    """Publish one corpus chain over synthetic documents without external tools."""
    sources = tmp_path / "sources"
    sources.mkdir(parents=True, exist_ok=True)
    chosen_fixtures = FIXTURES if fixtures is None else fixtures
    for name, payload in chosen_fixtures.items():
        (sources / name).write_text(payload, encoding="utf-8", newline="")
    for name, payload in (raw_fixtures or {}).items():
        (sources / name).write_bytes(payload)
    context = StageContext(
        "inventory",
        "run-chain",
        "run-chain",
        (SiloRoot("one", sources),),
        tmp_path / "results",
        {"project_root": str(Path.cwd()), "tmp_dir": str(tmp_path / "scratch")},
    )
    inventory = InventoryStage().run(context)
    extract = ExtractionStage(
        ExtractionPolicy(batch_rows=2), cast(TieredExtractor, router or ChainRouter())
    ).run(replace(context, stage="extract"))
    normalize = NormalizeStage(NormalizePolicy(batch_rows=2)).run(
        replace(
            context,
            stage="normalize",
            options=_pointer(context, "extraction", extract, "documents"),
        )
    )
    dedupe = DedupeStage(dedupe_policy or DedupePolicy(batch_rows=2, min_sketch_shingles=1)).run(
        replace(
            context,
            stage="dedupe",
            options=_pointer(context, "normalization", normalize, "normalized-documents"),
        )
    )
    chunk = ChunkStage(
        chunk_policy or ChunkPolicy(batch_rows=2, target_chars=90, min_chars=20)
    ).run(
        replace(
            context,
            stage="chunk",
            options={
                **_pointer(context, "normalization", normalize, "normalized-documents"),
                **_pointer(context, "dedupe", dedupe, "duplicate-groups"),
            },
        )
    )
    return ChainRun(context, inventory, extract, normalize, dedupe, chunk)


def _pointer(context: StageContext, name: str, result: StageResult, dataset: str) -> dict[str, str]:
    output = next(item for item in result.outputs if item.dataset == dataset)
    manifest = Path(output.partition["manifest"])
    return {
        **dict(context.options),
        f"{name}_manifest": str(manifest),
        f"{name}_manifest_sha256": hash_file(manifest)[0],
    }
