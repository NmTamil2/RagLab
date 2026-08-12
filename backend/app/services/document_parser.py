"""PDF text extraction.

This module is the only place in the codebase that knows PyMuPDF exists. It
takes a path to a PDF and returns page-level text; it does not know about HTTP,
about where documents are stored, or about what happens to the text next.

Keeping it that narrow means later milestones (chunking, embedding) can call
`extract_pages()` from a script or a background job, and swapping the PDF
library one day would touch this file only.
"""

import logging
import re
from pathlib import Path

import pymupdf

from app.models.document import PageText

logger = logging.getLogger(__name__)


class DocumentParseError(Exception):
    """The parser failed for a reason we did not anticipate."""


class CorruptedPdfError(DocumentParseError):
    """The file could not be opened as a PDF: truncated, damaged or not a PDF."""


class ProtectedPdfError(DocumentParseError):
    """The PDF is encrypted and needs a password we do not have."""


class NoExtractableTextError(DocumentParseError):
    """The PDF opened fine but every page came back empty.

    Usually means a scanned document — images of text, with no text layer.
    Reading those needs OCR, which is not part of this milestone.
    """


# PDFs frequently contain non-breaking spaces where a normal space is meant.
# Left in, they show up as odd characters downstream, so they are normalised.
NON_BREAKING_SPACE = " "

# Three or more newlines in a row (blank line after blank line) carry no
# meaning; two is enough to mark a paragraph break.
EXCESS_BLANK_LINES = re.compile(r"\n{3,}")


def _clean_page_text(raw_text: str) -> str:
    """Tidy obvious whitespace noise without changing the words.

    Deliberately conservative: it removes trailing spaces, collapses runs of
    blank lines and normalises non-breaking spaces. It does NOT collapse spaces
    inside a line or re-join lines, because that would quietly destroy layout
    information (tables, columns) that later steps may want.
    """
    text = raw_text.replace(NON_BREAKING_SPACE, " ")

    # splitlines() also handles the \r\n and \r line endings some PDFs produce.
    text = "\n".join(line.rstrip() for line in text.splitlines())

    text = EXCESS_BLANK_LINES.sub("\n\n", text)

    return text.strip()


def extract_pages(pdf_path: Path) -> list[PageText]:
    """Extract the text of every page of a PDF, in document order.

    Pages that contain no text are kept with an empty `text` value rather than
    dropped, so `pages[i].page_number` always matches the real PDF page and a
    document's page count is never silently wrong.

    Args:
        pdf_path: Absolute path to a PDF file that already exists on disk.

    Returns:
        One PageText per page, ordered from page 1.

    Raises:
        CorruptedPdfError: the file could not be opened as a PDF.
        ProtectedPdfError: the PDF is password-protected.
        NoExtractableTextError: the PDF has no text layer at all.
        DocumentParseError: any other failure while reading the file.
    """
    try:
        # Read the bytes ourselves rather than handing PyMuPDF the path. When
        # PyMuPDF opens a path and then fails on a damaged file, it can hold on
        # to the OS file handle — on Windows that leaves the upload locked, so
        # it cannot be deleted or replaced until the server restarts. Reading
        # first means Python closes the file immediately, whatever happens next.
        # The upload size limit keeps this bounded.
        pdf_bytes = pdf_path.read_bytes()
    except OSError as error:
        logger.exception("Could not read %s", pdf_path)
        raise DocumentParseError("The PDF could not be read from storage.") from error

    try:
        # `with` guarantees the document is closed even if extraction raises
        # halfway through: MuPDF also holds native memory that Python's garbage
        # collector does not manage for us.
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf_document:
            if pdf_document.needs_pass:
                raise ProtectedPdfError(
                    "This PDF is password-protected, so its text cannot be read."
                )

            pages = [
                PageText(
                    # PyMuPDF indexes pages from 0; humans and citations count
                    # from 1. We convert once, here, and never again.
                    page_number=page.number + 1,
                    text=_clean_page_text(page.get_text("text")),
                )
                for page in pdf_document
            ]

    except ProtectedPdfError:
        # Raised by us just above; let it through untouched.
        raise
    except pymupdf.FileDataError as error:
        # Covers both a damaged/truncated PDF and a zero-byte file.
        raise CorruptedPdfError(
            "The PDF could not be opened. It may be corrupted or incomplete."
        ) from error
    except Exception as error:
        logger.exception("Unexpected failure while parsing %s", pdf_path)
        raise DocumentParseError("The PDF could not be processed.") from error

    if not any(page.text for page in pages):
        raise NoExtractableTextError(
            "No text could be extracted. The PDF may be a scanned image, "
            "which needs OCR."
        )

    logger.info("Extracted %d pages from %s", len(pages), pdf_path.name)

    return pages
