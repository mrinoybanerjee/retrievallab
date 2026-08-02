from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

import fitz  # type: ignore[import-untyped]

from retrievallab.models import Chunk
from retrievallab.text import token_windows

MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_PAGES = 200
MIN_EXTRACTED_CHARACTERS = 80


class IngestionError(ValueError):
    def __init__(self, code: str, message: str, fix: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.fix = fix


@dataclass(frozen=True, slots=True)
class IngestedDocument:
    document_id: str
    filename: str
    page_count: int
    chunk_count: int
    chunks: list[Chunk]


def _safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", filename).strip("-.")
    return cleaned[:90] or "document.pdf"


def ingest_pdf(
    payload: bytes,
    filename: str,
    *,
    child_tokens: int = 500,
    overlap_tokens: int = 50,
) -> IngestedDocument:
    if len(payload) > MAX_FILE_BYTES:
        raise IngestionError("file_too_large", "The PDF is larger than 20 MB.", "Upload a PDF of 20 MB or less.")
    if not payload.startswith(b"%PDF-"):
        raise IngestionError(
            "invalid_pdf", "The upload does not contain PDF magic bytes.", "Export the source as a valid PDF and retry."
        )
    if not 50 <= child_tokens <= 1_500 or not 0 <= overlap_tokens < child_tokens:
        raise IngestionError(
            "invalid_chunking",
            "The chunking configuration is invalid.",
            "Use 50–1500 child tokens and overlap smaller than the child size.",
        )

    try:
        document = fitz.open(stream=payload, filetype="pdf")
    except Exception as error:
        raise IngestionError(
            "unreadable_pdf", "The PDF parser could not open this file.", "Repair or re-export the PDF and retry."
        ) from error
    if document.needs_pass:
        raise IngestionError(
            "encrypted_pdf",
            "Encrypted PDFs are not supported in v0.1.",
            "Remove the password or upload an unencrypted copy.",
        )
    if document.page_count > MAX_PAGES:
        raise IngestionError(
            "too_many_pages",
            f"The PDF has {document.page_count} pages; the limit is {MAX_PAGES}.",
            "Split the document into smaller files.",
        )

    digest = hashlib.sha256(payload).hexdigest()[:16]
    source = _safe_filename(filename)
    chunks: list[Chunk] = []
    total_characters = 0
    for page_index, page in enumerate(document, start=1):
        blocks = [block for block in page.get_text("blocks") if len(block) >= 5 and str(block[4]).strip()]
        page_text = " ".join(" ".join(str(block[4]).split()) for block in blocks)
        total_characters += len(page_text)
        windows = token_windows(page_text, child_tokens, overlap_tokens)
        if not windows:
            continue
        page_bounds = (
            float(page.rect.x0),
            float(page.rect.y0),
            float(page.rect.x1),
            float(page.rect.y1),
        )
        for child_index, (excerpt, start, end) in enumerate(windows):
            chunks.append(
                Chunk(
                    id=f"{digest}-p{page_index}-c{child_index}",
                    parent_id=f"{digest}-p{page_index}",
                    source=source,
                    page=page_index,
                    section=f"Page {page_index}",
                    text=excerpt,
                    token_start=start,
                    token_end=end,
                    metadata={"document_id": digest, "filename": source},
                    coordinates=page_bounds,
                )
            )
    page_count = document.page_count
    document.close()

    if total_characters < MIN_EXTRACTED_CHARACTERS or not chunks:
        raise IngestionError(
            "no_text_layer",
            "The PDF does not contain enough extractable text and may be scanned.",
            "Run OCR before uploading. OCR is intentionally not performed silently.",
        )
    return IngestedDocument(digest, source, page_count, len(chunks), chunks)
