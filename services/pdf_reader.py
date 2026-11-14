from pypdf import PdfReader

from config import CHUNK_OVERLAP, CHUNK_SIZE


def split_text(text):
    """Cut a long text into overlapping pieces."""
    text = " ".join(text.split())
    if not text:
        return []

    pieces = []
    start = 0
    step = CHUNK_SIZE - CHUNK_OVERLAP
    while start < len(text):
        pieces.append(text[start:start + CHUNK_SIZE])
        start += step
    return pieces


def read_pdf_chunks(pdf_path):
    """Return a list of (page_number, chunk_text) for one PDF."""
    reader = PdfReader(str(pdf_path))
    chunks = []
    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        for piece in split_text(page_text):
            chunks.append((page_number, piece))
    return chunks
