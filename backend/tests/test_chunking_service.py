"""Tests for the chunking service.

Run from the backend/ folder:  pytest

No PDFs here. The chunker takes plain page objects, so these tests build text of
an exact length and check exactly where the cuts land — which is the whole point
of a character-based algorithm.
"""

import pytest

from app.models.chunk import Chunk
from app.models.document import PageText
from app.services.chunking_service import (
    ChunkingConfig,
    InvalidChunkConfigError,
    chunk_pages,
    normalize_whitespace,
    split_text,
)

DOCUMENT_ID = "3f1c9f0e-7b2a-4a1e-9f5b-2c8d0e4a6b31"

# Small numbers keep the expectations readable: with size 10 and overlap 3 the
# window steps forward 7 characters at a time, which is easy to check by eye.
SMALL = ChunkingConfig(chunk_size=10, chunk_overlap=3)


def page(text: str, page_number: int = 1) -> PageText:
    """A page of text, as the PDF parser would hand it over."""
    return PageText(page_number=page_number, text=text)


# --- Configuration validation ------------------------------------------------


def test_chunk_size_must_be_positive():
    with pytest.raises(InvalidChunkConfigError):
        ChunkingConfig(chunk_size=0, chunk_overlap=0)


def test_chunk_overlap_cannot_be_negative():
    with pytest.raises(InvalidChunkConfigError):
        ChunkingConfig(chunk_size=100, chunk_overlap=-1)


def test_overlap_equal_to_chunk_size_is_rejected():
    # The dangerous case: the window would never move forward, so chunking
    # would loop forever. It must fail loudly instead.
    with pytest.raises(InvalidChunkConfigError):
        ChunkingConfig(chunk_size=100, chunk_overlap=100)


def test_overlap_larger_than_chunk_size_is_rejected():
    with pytest.raises(InvalidChunkConfigError):
        ChunkingConfig(chunk_size=100, chunk_overlap=150)


def test_zero_overlap_is_allowed():
    config = ChunkingConfig(chunk_size=100, chunk_overlap=0)

    assert config.step == 100


def test_step_is_size_minus_overlap():
    assert ChunkingConfig(chunk_size=500, chunk_overlap=50).step == 450


# --- Whitespace normalisation ------------------------------------------------


def test_whitespace_runs_collapse_to_single_spaces():
    assert normalize_whitespace("Sensor   fusion\n\n  combines\tinputs\n") == (
        "Sensor fusion combines inputs"
    )


def test_normalising_whitespace_only_text_gives_an_empty_string():
    assert normalize_whitespace("   \n\n\t  ") == ""


# --- Splitting ---------------------------------------------------------------


def test_text_shorter_than_chunk_size_becomes_one_chunk():
    pieces = split_text("short", SMALL)

    assert pieces == ["short"]


def test_text_exactly_chunk_size_becomes_one_chunk():
    text = "0123456789"  # exactly 10 characters

    pieces = split_text(text, SMALL)

    # The boundary case worth pinning down: no stray second chunk containing
    # only the tail of the first.
    assert pieces == [text]


def test_text_longer_than_chunk_size_is_split():
    text = "abcdefghijklmnopqrstuvwxyz"  # 26 characters

    pieces = split_text(text, SMALL)

    # size 10, overlap 3 -> windows start at 0, 7, 14, 21
    assert pieces == ["abcdefghij", "hijklmnopq", "opqrstuvwx", "vwxyz"]


def test_consecutive_chunks_overlap_by_the_configured_amount():
    text = "abcdefghijklmnopqrstuvwxyz"

    pieces = split_text(text, SMALL)

    # The last 3 characters of each chunk are the first 3 of the next one.
    for current, following in zip(pieces, pieces[1:]):
        assert current[-SMALL.chunk_overlap :] == following[: SMALL.chunk_overlap]


def test_zero_overlap_produces_chunks_that_do_not_repeat_text():
    config = ChunkingConfig(chunk_size=10, chunk_overlap=0)

    pieces = split_text("abcdefghijklmnopqrstuvwxyz", config)

    assert pieces == ["abcdefghij", "klmnopqrst", "uvwxyz"]
    assert "".join(pieces) == "abcdefghijklmnopqrstuvwxyz"


def test_empty_text_produces_no_chunks():
    assert split_text("", SMALL) == []


def test_whitespace_only_text_produces_no_chunks():
    assert split_text("      ", SMALL) == []


def test_the_documented_500_50_example_lands_where_it_should():
    # The example from the milestone brief, checked literally: with size 500 and
    # overlap 50, chunk 2 must start at character 450 of the original text.
    config = ChunkingConfig(chunk_size=500, chunk_overlap=50)
    text = "x" * 1000
    marked = "A" + text[1:450] + "B" + text[451:]  # markers at index 0 and 450

    pieces = split_text(marked, config)

    assert len(pieces) == 3
    assert pieces[0][0] == "A"
    assert pieces[1][0] == "B"
    assert [len(piece) for piece in pieces] == [500, 500, 100]


# --- Chunking pages ----------------------------------------------------------


def test_a_page_shorter_than_the_chunk_size_gives_one_chunk():
    chunks = chunk_pages([page("Short")], DOCUMENT_ID, SMALL)

    assert len(chunks) == 1
    assert isinstance(chunks[0], Chunk)
    assert chunks[0].text == "Short"
    assert chunks[0].chunk_index == 0


def test_one_page_can_become_several_chunks():
    chunks = chunk_pages([page("abcdefghijklmnopqrstuvwxyz")], DOCUMENT_ID, SMALL)

    assert len(chunks) == 4
    # Every chunk still points at the single page they all came from.
    assert {chunk.page_number for chunk in chunks} == {1}


def test_page_numbers_are_preserved_across_pages():
    chunks = chunk_pages(
        [page("First page", 1), page("Second page", 2), page("Third page", 3)],
        DOCUMENT_ID,
        ChunkingConfig(chunk_size=100, chunk_overlap=10),
    )

    assert [chunk.page_number for chunk in chunks] == [1, 2, 3]
    assert chunks[1].text == "Second page"


def test_chunks_never_mix_text_from_two_pages():
    chunks = chunk_pages(
        [page("aaaa", 1), page("bbbb", 2)],
        DOCUMENT_ID,
        ChunkingConfig(chunk_size=100, chunk_overlap=0),
    )

    # A chunk large enough to hold both pages still holds only one, because
    # each page is chunked on its own. This is what keeps page_number exact.
    assert [chunk.text for chunk in chunks] == ["aaaa", "bbbb"]


def test_pages_without_text_are_skipped_without_shifting_page_numbers():
    chunks = chunk_pages(
        [page("Real text", 1), page("", 2), page("More text", 3)],
        DOCUMENT_ID,
        ChunkingConfig(chunk_size=100, chunk_overlap=10),
    )

    assert len(chunks) == 2
    # Page 2 contributed nothing, and page 3 is still reported as page 3.
    assert [chunk.page_number for chunk in chunks] == [1, 3]


def test_a_document_with_no_text_at_all_produces_no_chunks():
    chunks = chunk_pages([page("", 1), page("   ", 2)], DOCUMENT_ID, SMALL)

    assert chunks == []


def test_chunk_indexes_count_up_across_the_whole_document():
    chunks = chunk_pages(
        [page("abcdefghijklmnop", 1), page("qrstuvwxyz", 2)],
        DOCUMENT_ID,
        SMALL,
    )

    # Continuous, gap-free, and in reading order — not restarted per page.
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))


def test_chunk_ids_are_unique_and_describe_where_the_chunk_came_from():
    chunks = chunk_pages(
        [page("abcdefghijklmnop", 1), page("qrstuvwxyz", 2)],
        DOCUMENT_ID,
        SMALL,
    )

    ids = [chunk.chunk_id for chunk in chunks]

    assert len(set(ids)) == len(ids)
    assert ids[0] == f"{DOCUMENT_ID}-p1-c0"
    assert ids[-1] == f"{DOCUMENT_ID}-p2-c{len(chunks) - 1}"


def test_chunking_the_same_document_twice_gives_the_same_ids():
    pages = [page("abcdefghijklmnopqrstuvwxyz")]

    first = chunk_pages(pages, DOCUMENT_ID, SMALL)
    second = chunk_pages(pages, DOCUMENT_ID, SMALL)

    # IDs are derived, not random, so re-running does not create duplicates in
    # whatever storage they end up in later.
    assert [chunk.chunk_id for chunk in first] == [
        chunk.chunk_id for chunk in second
    ]


def test_every_chunk_carries_the_document_id_and_a_matching_char_count():
    chunks = chunk_pages([page("abcdefghijklmnopqrstuvwxyz")], DOCUMENT_ID, SMALL)

    for chunk in chunks:
        assert chunk.document_id == DOCUMENT_ID
        assert chunk.char_count == len(chunk.text)


def test_windows_that_contain_only_whitespace_are_dropped():
    # A gap wider than the window means some windows see nothing but spaces.
    # Those must not become empty chunks. (chunk_pages normalises whitespace
    # away first, so this guard is checked on split_text directly.)
    config = ChunkingConfig(chunk_size=10, chunk_overlap=0)

    pieces = split_text("word" + " " * 40 + "word", config)

    assert pieces == ["word", "word"]


def test_page_text_is_normalised_before_being_chunked():
    chunks = chunk_pages(
        [page("Sensor   fusion\n\ncombines\tinputs")],
        DOCUMENT_ID,
        ChunkingConfig(chunk_size=100, chunk_overlap=10),
    )

    assert chunks[0].text == "Sensor fusion combines inputs"
