"""Structure, table-header, and sentence chunker behavior."""

from arxiv_int.pipeline.chunk.assemble import chunk_document
from arxiv_int.pipeline.chunk.blocks import HEADING, PROSE, TABLE, blocks
from arxiv_int.pipeline.chunk.model import TABLE_CHUNK, TEXT_CHUNK, ChunkPolicy
from arxiv_int.pipeline.chunk.sentences import sentence_spans
from arxiv_int.pipeline.chunk.tables import table_chunks

POLICY = ChunkPolicy(target_chars=80, min_chars=20, max_chars=160)


def test_blocks_classify_headings_tables_and_prose() -> None:
    text = (
        "OTCHET 2024\n"
        "\n"
        "| Item | Amount |\n"
        "| --- | --- |\n"
        "| Bolt | 100 |\n"
        "| Nut | 200 |\n"
        "\n"
        "1. Vvedenie\n"
        "\n"
        "Postavka vypolnena v srok. Priemka provedena komissiej.\n"
    )
    kinds = [block.kind for block in blocks(text, POLICY)]
    assert kinds == [HEADING, TABLE, HEADING, PROSE]


def test_sentence_spans_keep_abbreviations_inside_one_sentence() -> None:
    text = "Postavka ot A. Ivanova vypolnena. Akt podpisan."
    spans = sentence_spans(text, 0)
    assert [text[start:end].strip() for start, end in spans] == [
        "Postavka ot A. Ivanova vypolnena.",
        "Akt podpisan.",
    ]


def test_table_chunks_repeat_the_header_in_every_row_group() -> None:
    text = (
        "| Item | Amount |\n"
        "| --- | --- |\n"
        "| Bolt | 100 kg |\n"
        "| Nut | 200 kg |\n"
        "| Washer | 300 kg |\n"
    )
    produced = table_chunks(blocks(text, POLICY)[0], POLICY, 0)
    assert produced
    assert all(chunk.kind == TABLE_CHUNK for chunk in produced)
    assert all(chunk.text.startswith("| Item | Amount |") for chunk in produced)
    assert all(chunk.prefix_span == (0, text.index("\n")) for chunk in produced)


def test_chunk_document_keeps_section_path_and_source_offsets() -> None:
    text = (
        "1. Vvedenie\n"
        "\n"
        "Postavka vypolnena v srok. Priemka provedena komissiej. "
        "Zamechanij po kachestvu net.\n"
    )
    produced = chunk_document(text, POLICY)
    assert produced.chunks
    assert produced.chunks[0].kind == TEXT_CHUNK
    assert produced.chunks[0].section_path == ("1. Vvedenie",)
    first = produced.chunks[0]
    assert text[first.start : first.end] == first.text
