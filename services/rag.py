from config import LLM_API_KEY
from services.llm import ask_with_fallback
from services.vector_store import find_relevant_chunks

SYSTEM_PROMPT = (
    "You answer questions using only the document excerpts given to you. "
    "If the excerpts do not contain the answer, say you could not find it in the "
    "documents instead of guessing. Reply in the same language the user asked in. "
    "Keep answers clear and short."
)


def build_prompt(question, chunks):
    excerpts = []
    for number, chunk in enumerate(chunks, start=1):
        header = f"[{number}] {chunk['source']}, page {chunk['page']}"
        excerpts.append(f"{header}\n{chunk['text']}")
    context = "\n\n".join(excerpts)
    return f"Document excerpts:\n\n{context}\n\nQuestion: {question}"


def format_sources(chunks):
    seen = []
    for chunk in chunks:
        label = f"{chunk['source']} (p. {chunk['page']})"
        if label not in seen:
            seen.append(label)
    return seen


def answer_question(question):
    """Returns (answer_text, list_of_sources). Raises on API problems."""
    if not LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY is missing. Add it to the .env file.")

    chunks = find_relevant_chunks(question)
    if not chunks:
        return "No documents are indexed yet. Put some PDFs in the documents folder.", []

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_prompt(question, chunks)},
    ]
    return ask_with_fallback(messages), format_sources(chunks)
