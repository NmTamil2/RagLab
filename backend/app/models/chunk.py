"""Response models for the chunking endpoint.

A chunk is a short piece of a document's text, small enough to be embedded and
searched later. The models here describe one chunk and the result of chunking a
whole document.

The important idea: a chunk is never a bare string. It always travels with the
metadata saying where it came from — which document, which page, and where it
sits in the sequence. Once that link is broken it cannot be rebuilt, and a
retrieval result with no page number cannot be cited.
"""

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """One piece of a document's text, with the metadata that locates it."""

    chunk_id: str = Field(
        description=(
            "Unique, stable ID of this chunk. Built from the document ID, the "
            "page number and the chunk index, so it is readable and the same "
            "text always gets the same ID when re-chunked with the same config."
        ),
        examples=["3f1c9f0e-7b2a-4a1e-9f5b-2c8d0e4a6b31-p1-c0"],
    )
    document_id: str = Field(
        description="ID of the document this chunk was taken from.",
        examples=["3f1c9f0e-7b2a-4a1e-9f5b-2c8d0e4a6b31"],
    )
    page_number: int = Field(
        description=(
            "1-based PDF page this chunk's text came from. Chunks never span "
            "pages, so this is a single exact number rather than a range."
        ),
        examples=[1],
    )
    chunk_index: int = Field(
        description=(
            "Position of this chunk in the document, counting from 0 across "
            "all pages. Chunk 5 always follows chunk 4, even over a page break."
        ),
        examples=[0],
    )
    char_count: int = Field(
        description=(
            "Length of `text` in characters. Always equals len(text); included "
            "so chunk sizes can be inspected without measuring the text itself."
        ),
        examples=[500],
    )
    text: str = Field(
        description="The chunk's text. Never empty.",
        examples=["Advanced Driver Assistance Systems help the driver by ..."],
    )


class DocumentChunks(BaseModel):
    """What the API returns after a document has been chunked.

    The configuration that produced the chunks is echoed back deliberately.
    When you compare two runs with different settings, the response itself says
    which settings it came from — you never have to remember what the server
    was configured with at the time.
    """

    document_id: str = Field(
        description="ID of the document that was chunked.",
        examples=["3f1c9f0e-7b2a-4a1e-9f5b-2c8d0e4a6b31"],
    )
    filename: str = Field(
        description="Original filename, so results stay readable to a human.",
        examples=["adas.pdf"],
    )
    page_count: int = Field(
        description="Number of pages the PDF had, including any with no text.",
        examples=[3],
    )
    chunk_count: int = Field(
        description="Number of chunks produced, equal to len(chunks).",
        examples=[10],
    )
    chunk_size: int = Field(
        description="Chunk size, in characters, used for this run.",
        examples=[500],
    )
    chunk_overlap: int = Field(
        description="Overlap, in characters, used for this run.",
        examples=[50],
    )
    chunks: list[Chunk] = Field(
        description="The chunks, in document order.",
    )
