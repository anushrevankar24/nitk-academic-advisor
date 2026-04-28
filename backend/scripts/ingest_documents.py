#!/usr/bin/env python3
"""
Document ingestion pipeline for academic PDFs.

This script provides a clean, reliable setup for processing academic PDFs
with semantic chunking, e5-base-v2 embeddings and GPU optimization.

Usage:
    python scripts/ingest_documents.py

Features:
- Semantic chunking optimized for academic PDFs (600-800 tokens, 100 overlap)
- e5-base-v2 embeddings with GPU acceleration
- Automatic removal of repetitive institutional headers and footers
- Clean, maintainable code using modern document processing
- Automatic GPU detection and optimization
- Built-in BM25 index creation for hybrid retrieval
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.document_processor import DocumentProcessor
from src.utils.config import PDF_DIR, DATA_DIR, BTECH_PDF_URL, PG_PDF_URL
from urllib.parse import urlparse
from urllib.request import urlretrieve


def ensure_pdfs_available() -> None:
    """Ensure required PDFs exist; download from URLs if missing."""
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    existing_pdfs = list(PDF_DIR.glob("*.pdf"))
    if existing_pdfs:
        return

    urls = []
    if BTECH_PDF_URL:
        urls.append(BTECH_PDF_URL)
    if PG_PDF_URL:
        urls.append(PG_PDF_URL)

    if not urls:
        print(f"No PDFs found in {PDF_DIR} and no PDF URLs provided in environment.")
        print("Set BTECH_PDF_URL and/or PG_PDF_URL in .env, or place PDFs in data/pdfs/.")
        return

    print(f"No PDFs found locally. Attempting to download {len(urls)} file(s)...")
    for url in urls:
        try:
            filename = Path(urlparse(url).path).name or "document.pdf"
            dest = PDF_DIR / filename
            print(f"  Downloading {url} -> {dest}")
            urlretrieve(url, dest)
        except Exception as e:
            print(f"  Failed to download {url}: {e}")
            continue

    downloaded = list(PDF_DIR.glob("*.pdf"))
    if not downloaded:
        print("Failed to download any PDFs. Please check URLs or network and retry.")
    else:
        print(f"Downloaded {len(downloaded)} PDF(s) to {PDF_DIR}")


def main():
    """Run the document ingestion pipeline."""
    
    # Ensure PDFs are present (download if configured)
    ensure_pdfs_available()
    
    if not PDF_DIR.exists():
        print(f"PDF directory not found: {PDF_DIR}")
        return 1
    
    pdf_files = list(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {PDF_DIR}")
        print("Provide PDFs or set BTECH_PDF_URL / PG_PDF_URL in .env")
        return 1
    
    print(f"Found {len(pdf_files)} PDF files:")
    for pdf_file in pdf_files:
        print(f"  - {pdf_file.name}")
    
    # Initialize processor with requested parameters
    processor = DocumentProcessor(
        chunk_size=1000,
        chunk_overlap=200,
        embedding_model="intfloat/e5-base-v2",
        device="auto",  # Auto-detect GPU
        clean_headers=True,  # Enable header cleaning to remove repetitive institutional content
        log_chunks=True  # Enable chunk logging to logs/chunks_loaded.log
    )
    
    # Process PDFs
    try:
        results = processor.process_pdfs(PDF_DIR, DATA_DIR)
        
        print("\n" + "=" * 60)
        print("SUCCESS! Ingestion Complete")
        print("=" * 60)
        print(f"Pages processed: {results['documents']}")
        print(f"Chunks created: {results['chunks']}")
        print(f"Chunks file: {results['chunks_file']}")
        print(f"FAISS storage: {results['faiss_path']}")
        print(f"Chunk log file: logs/chunks_loaded.log")
        print("\nNext steps:")
        print("1. Start the API server: uvicorn src.api.main:app --reload")
        print("2. Test the chatbot at http://localhost:8000")
        print("3. Check logs/chunks_loaded.log to see all loaded chunks")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError during processing: {e}")
        print("Please check the error message and try again.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
