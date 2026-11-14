import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent

# Secrets come from .env only, it is gitignored.
# Works with any OpenAI-compatible provider (Groq, OpenAI, Ollama, ...)
load_dotenv(BASE_DIR / ".env")

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
# One model, or several separated by commas. If one is busy the next is tried.
LLM_MODELS = [
    name.strip()
    for name in os.getenv("LLM_MODEL", "llama-3.3-70b-versatile").split(",")
    if name.strip()
]
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "512"))  # some providers cap this

DOCS_DIR = BASE_DIR / "documents"
DB_DIR = BASE_DIR / "chroma_db"
COLLECTION_NAME = "pdf_chunks"

CHUNK_SIZE = 1000      # characters per chunk
CHUNK_OVERLAP = 150    # characters shared between neighbouring chunks
TOP_K = 5              # how many chunks we send to the model

WATCH_INTERVAL_MS = 5000  # how often the widget checks the folder for new PDFs
