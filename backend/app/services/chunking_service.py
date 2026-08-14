"""Document chunking.

Embedding models and language models both have a size limit, and searching a
whole 40-page document as one unit is useless anyway — you would get back the
entire document for every question. So the text is cut into small overlapping
pieces called *chunks*, and it is chunks, not documents, that get embedded,
searched and quoted later.

This module does that cutting, and nothing else. It knows nothing about HTTP,
about PDFs, or about where documents are stored: it takes page-level text plus a
configuration, and returns chunks. That makes it the easiest part of the project
to test and to experiment with.

The algorithm here is deliberately the simplest one that works — a fixed-size
character window that slides forward. No LangChain, no tokenizers, no sentence
splitting. Read it top to bottom and you will know exactly what a chunk is.
"""

import logging
from dataclasses import dataclass

from app.core.config import settings
from app.models.chunk import Chunk
from app.models.document import PageText

logger = logging.getLogger(__name__)


class InvalidChunkConfigError(ValueError):
    """The requested chunk size / overlap combination cannot be used."""


@dataclass(frozen=True)
class ChunkingConfig:
    """The two numbers that control chunking, validated once on creation.

    Frozen (immutable) on purpose: a config object is handed to the chunker and
    echoed back in the response, so nothing should be able to change it halfway
    through a run and leave the response describing settings that were not used.

    Validating in the constructor means invalid settings cannot exist. Every
    function downstream can trust the values without re-checking them.
    """

    chunk_size: int
    chunk_overlap: int

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise InvalidChunkConfigError(
                f"chunk_size must be greater than 0, got {self.chunk_size}."
            )

        if self.chunk_overlap < 0:
            raise InvalidChunkConfigError(
                f"chunk_overlap cannot be negative, got {self.chunk_overlap}."
            )

        if self.chunk_overlap >= self.chunk_size:
            # Without this the window would never advance and chunking would
            # loop forever, producing the same chunk until memory ran out.
            raise InvalidChunkConfigError(
                f"chunk_overlap ({self.chunk_overlap}) must be smaller than "
                f"chunk_size ({self.chunk_size})."
            )

    @property
    def step(self) -> int:
        """How far the window moves between two chunks.

        With size 500 and overlap 50 the step is 450: each chunk starts 450
        characters after the previous one, so the first 50 characters of a chunk
        are the last 50 of the one before it. Guaranteed to be at least 1 by the
        validation above.
        """
        return self.chunk_size - self.chunk_overlap


def config_from_settings(
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> ChunkingConfig:
    """Build a config, falling back to the values in .env for anything omitted.

    This is the single bridge between application settings and the chunker. The
    chunking functions themselves never read `settings` — they are handed a
    config — which is why they can be tested with any values without touching
    the environment.

    Raises:
        InvalidChunkConfigError: the resulting combination is not usable.
    """
    return ChunkingConfig(
        chunk_size=settings.chunk_size if chunk_size is None else chunk_size,
        chunk_overlap=(
            settings.chunk_overlap if chunk_overlap is None else chunk_overlap
        ),
    )


def normalize_whitespace(text: str) -> str:
    """Collapse every run of whitespace into a single space.

    `str.split()` with no argument splits on any whitespace — spaces, tabs,
    newlines — and throws away empty pieces; joining with a single space puts
    the words back together evenly. So this one line turns

        "Sensor   fusion\\n\\n  combines\\tinputs\\n"

    into

        "Sensor fusion combines inputs"

    Why do it at all? Because chunk_size counts characters, and PDF text is full
    of line breaks and padding that are artefacts of page layout, not of the
    writing. Left in, a "500 character" chunk might be 480 characters of text
    and 20 characters of stray whitespace, and chunk boundaries would land in
    different places depending on how the PDF happened to be typeset.

    The cost is that paragraph structure is lost. That is acceptable here: this
    text exists to be embedded and searched, and the original layout is still
    available from the extract endpoint whenever a human wants to read it.
    """
    return " ".join(text.split())


def split_text(text: str, config: ChunkingConfig) -> list[str]:
    """Cut one piece of text into overlapping fixed-size pieces.

    The whole algorithm is a window that slides forward:

        chunk_size = 500, chunk_overlap = 50  ->  step = 450

        chunk 0: characters    0 .. 499
        chunk 1: characters  450 .. 949     (450-499 repeat chunk 0's ending)
        chunk 2: characters  900 .. 1399    (900-949 repeat chunk 1's ending)

    Two details that are easy to get wrong:

    * The loop stops as soon as a window reaches the end of the text. Without
      that check, text of length 520 would produce chunk 0 (0-499) and then
      chunk 1 (450-519) — a second chunk made entirely of characters the first
      one already contained.
    * Text shorter than one chunk is not a special case. The first window simply
      runs past the end, Python slicing returns what exists, and you get exactly
      one chunk. Nothing extra to write.

    Returns:
        The pieces in order. Empty list for text that is empty or all whitespace.
    """
    text = text.strip()

    if not text:
        return []

    pieces: list[str] = []
    start = 0

    while start < len(text):
        # Slicing past the end is safe in Python: text[900:1400] on a
        # 1000-character string simply returns characters 900-999.
        piece = text[start : start + config.chunk_size].strip()

        # A window can strip down to nothing (a run of spaces at a boundary).
        # Empty chunks are worthless to embed, so they are dropped rather than
        # stored — this is the "avoid empty chunks" rule.
        if piece:
            pieces.append(piece)

        # This window already reached the end, so any further window would only
        # re-cover text we have.
        if start + config.chunk_size >= len(text):
            break

        start += config.step

    return pieces


def chunk_pages(
    pages: list[PageText],
    document_id: str,
    config: ChunkingConfig,
) -> list[Chunk]:
    """Turn page-level text into chunks that remember where they came from.

    Each page is chunked on its own, so a chunk never contains text from two
    pages. See the module notes in the README for why that trade-off is worth
    making at this stage; the short version is that one exact page number per
    chunk is what makes a citation possible later.

    Pages with no extractable text (blank pages, or image-only pages) simply
    produce no chunks. They are not an error, and they do not shift the page
    numbers of anything else, because `page_number` comes from the page itself
    rather than from a running counter.

    Args:
        pages: Page-level text, as returned by the document parser.
        document_id: The document these pages belong to, recorded on every chunk.
        config: Validated chunk size and overlap.

    Returns:
        Chunks in document order. Empty list if no page held any text.
    """
    chunks: list[Chunk] = []

    for page in pages:
        clean_text = normalize_whitespace(page.text)

        for piece in split_text(clean_text, config):
            # chunk_index counts across the whole document, not per page, so
            # sorting by it always gives reading order.
            chunk_index = len(chunks)

            chunks.append(
                Chunk(
                    # Built from values rather than random: re-chunking the same
                    # document with the same settings reproduces the same IDs,
                    # which keeps the vector store consistent in a later
                    # milestone instead of filling up with duplicates. It is
                    # also readable — "...-p3-c12" tells you where you are.
                    chunk_id=f"{document_id}-p{page.page_number}-c{chunk_index}",
                    document_id=document_id,
                    page_number=page.page_number,
                    chunk_index=chunk_index,
                    char_count=len(piece),
                    text=piece,
                )
            )

    logger.info(
        "Chunked document %s into %d chunks (size=%d, overlap=%d)",
        document_id,
        len(chunks),
        config.chunk_size,
        config.chunk_overlap,
    )

    return chunks
