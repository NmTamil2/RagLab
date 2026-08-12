"""Tests for the PDF parser.

Run from the backend/ folder:  pytest

The PDFs used here are built with PyMuPDF at test time instead of being
committed as binary fixtures. That keeps the repository text-only, and makes
each test say plainly what kind of document it is about.
"""

from pathlib import Path

import pymupdf
import pytest

from app.models.document import PageText
from app.services.document_parser import (
    CorruptedPdfError,
    NoExtractableTextError,
    extract_pages,
)


def make_pdf(path: Path, page_texts: list[str]) -> Path:
    """Write a PDF at `path` with one page per entry in `page_texts`.

    An empty string produces a genuinely blank page — useful for checking that
    blank pages are preserved rather than skipped.
    """
    with pymupdf.open() as document:
        for text in page_texts:
            page = document.new_page()
            if text:
                page.insert_text((72, 72), text, fontsize=12)

        document.save(path)

    return path


def test_extracts_text_from_a_single_page_pdf(tmp_path):
    pdf_path = make_pdf(tmp_path / "simple.pdf", ["Retrieval Augmented Generation"])

    pages = extract_pages(pdf_path)

    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert "Retrieval Augmented Generation" in pages[0].text


def test_keeps_pages_separate_and_numbered_in_order(tmp_path):
    pdf_path = make_pdf(
        tmp_path / "multipage.pdf",
        ["First page text", "Second page text", "Third page text"],
    )

    pages = extract_pages(pdf_path)

    assert [page.page_number for page in pages] == [1, 2, 3]
    # The whole point of page-level extraction: text stays with its own page.
    assert "First" in pages[0].text
    assert "Second" in pages[1].text
    assert "Third" in pages[2].text


def test_blank_pages_are_kept_so_page_numbers_stay_correct(tmp_path):
    pdf_path = make_pdf(tmp_path / "with-blank.pdf", ["Page one", "", "Page three"])

    pages = extract_pages(pdf_path)

    assert len(pages) == 3
    assert pages[1].text == ""
    # If the blank page were dropped, page three would be reported as page two
    # and every future citation pointing at it would be wrong.
    assert pages[2].page_number == 3
    assert "Page three" in pages[2].text


def test_corrupted_pdf_is_rejected(tmp_path):
    corrupted = tmp_path / "corrupted.pdf"
    corrupted.write_bytes(b"%PDF-1.7\nthis is not really a pdf")

    with pytest.raises(CorruptedPdfError):
        extract_pages(corrupted)


def test_empty_file_is_rejected(tmp_path):
    empty = tmp_path / "empty.pdf"
    empty.write_bytes(b"")

    with pytest.raises(CorruptedPdfError):
        extract_pages(empty)


def test_the_file_is_released_whether_parsing_succeeds_or_fails(tmp_path):
    good = make_pdf(tmp_path / "good.pdf", ["Some text"])
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.7\nthis is not really a pdf")

    extract_pages(good)
    with pytest.raises(CorruptedPdfError):
        extract_pages(bad)

    # On Windows, deleting a file that something still holds open raises
    # PermissionError. Being able to delete both is the proof that the parser
    # let go of them — including on the failure path, which is easy to miss.
    good.unlink()
    bad.unlink()


def test_pdf_without_any_text_is_reported_clearly(tmp_path):
    # A valid PDF whose pages are all blank stands in for a scanned document:
    # it opens fine, but there is no text layer to read.
    pdf_path = make_pdf(tmp_path / "scanned.pdf", ["", ""])

    with pytest.raises(NoExtractableTextError):
        extract_pages(pdf_path)


def test_whitespace_is_tidied_without_losing_words(tmp_path):
    pdf_path = make_pdf(tmp_path / "whitespace.pdf", ["Clean me   "])

    pages = extract_pages(pdf_path)

    assert pages[0].text == "Clean me"


def test_returns_typed_page_models(tmp_path):
    # The parser returns the same model the API responds with, so a mismatch
    # between service and response shape cannot creep in.
    pdf_path = make_pdf(tmp_path / "typed.pdf", ["Anything"])

    pages = extract_pages(pdf_path)

    assert all(isinstance(page, PageText) for page in pages)
