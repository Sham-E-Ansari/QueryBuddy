import chromadb

from config import COLLECTION_NAME, DB_DIR, DOCS_DIR, TOP_K
from services.pdf_reader import read_pdf_chunks


def get_collection():
    client = chromadb.PersistentClient(path=str(DB_DIR))
    return client.get_or_create_collection(COLLECTION_NAME)


def get_indexed_files(collection):
    """Map of filename -> modified time for everything already stored."""
    stored = collection.get(include=["metadatas"])
    indexed = {}
    for meta in stored["metadatas"]:
        indexed[meta["source"]] = meta["mtime"]
    return indexed


def add_pdf(collection, pdf_path):
    chunks = read_pdf_chunks(pdf_path)
    if not chunks:
        return 0

    mtime = pdf_path.stat().st_mtime
    collection.add(
        ids=[f"{pdf_path.name}::{i}" for i in range(len(chunks))],
        documents=[text for _, text in chunks],
        metadatas=[
            {"source": pdf_path.name, "page": page, "mtime": mtime}
            for page, _ in chunks
        ],
    )
    return len(chunks)


def remove_pdf(collection, filename):
    collection.delete(where={"source": filename})


def sync_documents():
    """Bring the database in line with the PDFs in the documents folder.

    Returns {"added": [...], "removed": [...]}.
    """
    DOCS_DIR.mkdir(exist_ok=True)
    collection = get_collection()
    indexed = get_indexed_files(collection)

    on_disk = {p.name: p for p in DOCS_DIR.glob("*.pdf")}
    added, removed = [], []

    # files that were deleted from the folder
    for filename in indexed:
        if filename not in on_disk:
            remove_pdf(collection, filename)
            removed.append(filename)

    # new files, or files that changed since last time
    for filename, path in on_disk.items():
        if indexed.get(filename) == path.stat().st_mtime:
            continue
        if filename in indexed:
            remove_pdf(collection, filename)
        add_pdf(collection, path)
        added.append(filename)

    return {"added": added, "removed": removed}


def folder_snapshot():
    """Cheap fingerprint of the folder, used to detect changes without reading PDFs."""
    if not DOCS_DIR.exists():
        return {}
    return {p.name: p.stat().st_mtime for p in DOCS_DIR.glob("*.pdf")}


def find_relevant_chunks(question):
    collection = get_collection()
    total = collection.count()
    if total == 0:
        return []

    result = collection.query(query_texts=[question], n_results=min(TOP_K, total))
    chunks = []
    for text, meta in zip(result["documents"][0], result["metadatas"][0]):
        chunks.append({"text": text, "source": meta["source"], "page": meta["page"]})
    return chunks
