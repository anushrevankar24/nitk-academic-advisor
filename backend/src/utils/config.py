"""Configuration management for NITK Academic Advisor RAG System."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / os.getenv("DATA_DIR", "data")
PDF_DIR = BASE_DIR / os.getenv("PDF_DIR", "data/pdfs")
CHUNKS_FILE = BASE_DIR / os.getenv("CHUNKS_FILE", "data/chunks_documents_v2.ndjson")
BM25_INDEX_FILE = BASE_DIR / os.getenv("BM25_INDEX_FILE", "data/bm25_index.pkl")

# API Configuration
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_RELOAD = os.getenv("API_RELOAD", "true").lower() == "true"

# OpenRouter API - with security validation
from .secrets import SecretsManager

OPENROUTER_API_KEY = SecretsManager.get_secret(
    "OPENROUTER_API_KEY",
    secret_file=BASE_DIR / ".secrets" / "openrouter_api_key" if (BASE_DIR / ".secrets" / "openrouter_api_key").exists() else None
)

# Validate API key on config load (fail fast)
if not SecretsManager.validate_api_key(OPENROUTER_API_KEY, "OPENROUTER_API_KEY"):
    print("ERROR: OPENROUTER_API_KEY is not set or invalid!", file=sys.stderr)
    print("   Please set it in .env file or OPENROUTER_API_KEY environment variable", file=sys.stderr)
    if os.getenv("ENV") == "production":
        sys.exit(1)  # Fail fast in production

# Document Processing Configuration
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
INGEST_VERSION = os.getenv("INGEST_VERSION", "v2")

# Model configurations
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/e5-base-v2")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "768"))
CROSS_ENCODER_MODEL = os.getenv("CROSS_ENCODER_MODEL", "BAAI/bge-reranker-large")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# FAISS configuration
FAISS_INDEX_FILE = BASE_DIR / os.getenv("FAISS_INDEX_FILE", "data/faiss_storage/documents_v2_index.bin")
FAISS_METADATA_FILE = BASE_DIR / os.getenv("FAISS_METADATA_FILE", "data/faiss_storage/documents_v2_metadata.pkl")

def _parse_int_env(name: str, default: int) -> int:
    value = os.getenv(name, str(default))
    # Strip inline comments and whitespace
    value = value.split('#', 1)[0].strip()
    try:
        return int(value)
    except ValueError:
        return default

def _parse_float_env(name: str, default: float) -> float:
    value = os.getenv(name, str(default))
    value = value.split('#', 1)[0].strip()
    try:
        return float(value)
    except ValueError:
        return default

# Retrieval parameters - Optimized for quality
TOP_K_VECTOR = _parse_int_env("TOP_K_VECTOR", 50)
TOP_K_BM25 = _parse_int_env("TOP_K_BM25", 50)
TOP_K_HYBRID = _parse_int_env("TOP_K_HYBRID", 100)
TOP_K_RERANK = _parse_int_env("TOP_K_RERANK", 20)
FINAL_TOP_K = _parse_int_env("FINAL_TOP_K", 10)

# Hybrid retrieval weights
HYBRID_ALPHA = _parse_float_env("HYBRID_ALPHA", 0.3)

# MMR parameters
FINAL_MMR_K = _parse_int_env("FINAL_MMR_K", FINAL_TOP_K)
MMR_LAMBDA = _parse_float_env("MMR_LAMBDA", 0.7)

# Batch processing - Optimized for speed
BATCH_SIZE_EMBEDDING = int(os.getenv("BATCH_SIZE_EMBEDDING", "16"))  # Reduced from 32

# Response Configuration
MIN_CONFIDENCE_THRESHOLD = float(os.getenv("MIN_CONFIDENCE_THRESHOLD", "0.3"))
HIGH_CONFIDENCE_THRESHOLD = float(os.getenv("HIGH_CONFIDENCE_THRESHOLD", "0.8"))

# Performance Configuration
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
RESPONSE_TIMEOUT = int(os.getenv("RESPONSE_TIMEOUT", "60"))

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
LOG_DIR = BASE_DIR / os.getenv("LOG_DIR", "logs")
CHUNK_LOG_FILE = LOG_DIR / "chunks_loaded.log"


# PDF source URLs (optional). If provided, ingestion can auto-download PDFs if missing.
BTECH_PDF_URL = os.getenv("BTECH_PDF_URL", "")
PG_PDF_URL = os.getenv("PG_PDF_URL", "")


