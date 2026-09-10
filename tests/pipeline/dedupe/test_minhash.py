import pytest

from arxiv_int.pipeline.dedupe.minhash import bands, shingles, similarity, sketch, tokens

_BINS = 128


def _words(count: int, offset: int = 0) -> list[str]:
    return [f"slovo{index + offset}" for index in range(count)]


def _sketch(words: list[str], size: int = 5) -> tuple[int, ...]:
    return sketch(shingles(words, size), _BINS)[0]


def test_tokens_drop_empty_fields_and_respect_the_budget() -> None:
    assert tokens("  dva   slova  ", 10) == ["dva", "slova"]
    assert tokens(" ".join(_words(40)), 8) == _words(8)


def test_shingles_slide_over_words_and_degrade_to_one_document_hash() -> None:
    assert len(list(shingles(_words(10), 5))) == 6
    assert len(list(shingles(_words(3), 5))) == 1
    assert list(shingles([], 5)) == []


def test_identical_token_streams_produce_identical_sketches() -> None:
    words = _words(200)

    assert _sketch(words) == _sketch(list(words))
    assert similarity(_sketch(words), _sketch(words)) == 1.0


def test_similarity_tracks_the_share_of_shared_shingles() -> None:
    base = _words(200)
    near = [*base]
    near[100] = "izmenenie"
    disjoint = _words(200, offset=1000)

    assert similarity(_sketch(base), _sketch(near)) >= 0.90
    assert similarity(_sketch(base), _sketch(disjoint)) <= 0.05


def test_sketches_stay_dense_when_shingles_are_scarcer_than_bins() -> None:
    signature, consumed = sketch(shingles(_words(6), 5), _BINS)

    assert consumed == 2
    assert len(signature) == _BINS
    assert len(set(signature)) > 1
    assert (1 << 64) - 1 not in signature


def test_bands_fold_the_sketch_into_locality_sensitive_keys() -> None:
    signature = _sketch(_words(200))
    keys = bands(signature, 4)

    assert len(keys) == _BINS // 4
    assert keys == bands(signature, 4)
    with pytest.raises(ValueError, match="multiple"):
        bands(signature, 7)


def test_similarity_refuses_mismatched_sketches() -> None:
    with pytest.raises(ValueError, match="length"):
        similarity((1, 2, 3), (1, 2))
