"""Deterministic, vocabulary-disjoint filler chunks that bring the corpus to archive scale.

Filler text shares only declared stopwords with the judged cases, so it can move
BM25 statistics, index size and latency without ever becoming a relevant hit.
"""

from collections.abc import Iterator
from itertools import accumulate
from random import Random

from arxiv_int.retrieval.second_opinion.splits import FillerVocabulary

FILLER_PREFIX = "so-filler"
FILLER_LANGUAGE = "rus"
CHUNKS_PER_DOCUMENT = 4
TITLE_WORDS = 3


def filler_rows(
    vocabulary: FillerVocabulary,
    *,
    chunks: int,
    min_words: int,
    max_words: int,
    stopword_share: float,
    seed: int,
) -> Iterator[dict[str, object]]:
    """Yield covering-table rows for ``chunks`` Zipf-distributed filler chunks."""
    if chunks < 0 or not 0 < min_words <= max_words or not 0.0 <= stopword_share < 1.0:
        raise ValueError("filler parameters are out of range")
    random = Random(seed)
    weights = list(accumulate(1.0 / (rank + 1) for rank in range(len(vocabulary.vocabulary))))
    offsets: dict[str, int] = {}
    for index in range(chunks):
        count = random.randint(min_words, max_words)
        words = [
            random.choice(vocabulary.stopwords)
            if random.random() < stopword_share
            else random.choices(vocabulary.vocabulary, cum_weights=weights)[0]
            for _ in range(count)
        ]
        body = " ".join(words).capitalize() + "."
        chunk_id = f"{FILLER_PREFIX}-{index:06d}"
        document_id = f"{FILLER_PREFIX}-doc-{index // CHUNKS_PER_DOCUMENT:06d}"
        start = offsets.get(document_id, 0)
        offsets[document_id] = start + len(body) + 2
        yield {
            "body": body,
            "chunk_id": chunk_id,
            "document_id": document_id,
            "end_char": start + len(body),
            "identifiers": chunk_id,
            "language": FILLER_LANGUAGE,
            "start_char": start,
            "title": " ".join(words[:TITLE_WORDS]),
        }
