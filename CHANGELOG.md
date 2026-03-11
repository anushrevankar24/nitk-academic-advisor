# Changelog

All notable changes to the NITK Academic Advisor RAG Chatbot project.

## [Unreleased] - 2026-01-16

### Added
- **Docker containerization** with multi-stage builds for CPU and GPU deployments
- **Security hardening**:
  - SecretsManager for multi-source credential management (env vars, Docker secrets, files)
  - SanitizingFormatter for automatic log redaction of sensitive data
  - API key validation with fail-fast behavior on startup
  - Comprehensive SECURITY.md guide with incident response procedures
- **NGINX reverse proxy** with rate limiting, security headers, gzip compression
- **Improved documentation**:
  - Comprehensive Copilot instructions for AI agent guidance
  - Updated DOCKER.md with clear ingestion vs API server workflows
  - Clarified that ingestion should run locally (faster than Docker)

### Fixed
- **Import error**: Fixed SecretsManager.validate_api_key import in config.py (was trying to import as standalone function)
- **Documentation**: Replaced all `docker-compose` commands with `docker compose` (V2 syntax)
- **Workflow clarity**: Added warning that ingestion takes 1-2 hours on CPU

### Changed
- **API error handling**: Generic error responses to clients, sensitive details only in server logs
- **Logging**: All print() statements replaced with sanitized logger calls
- **Configuration**: Centralized all security-sensitive operations in src/utils/

## [Previous] - 2024-01-XX

### Fixed

#### Issue #1: Excessive Header/Footer Noise in Chunks
- **Problem**: Chunks contained repetitive institutional headers like "NATIONAL INSTITUTE OF TECHNOLOGY KARNATAKA, SURATHKAL" appearing in almost every chunk
- **Solution**: 
  - Enhanced `clean_institutional_headers()` function in `src/utils/text_utils.py`
  - Added comprehensive header/footer pattern matching
  - Improved detection of short all-caps header lines
  - Made repetitive content removal less aggressive (threshold changed from 3 to 5 occurrences)
- **Files Modified**:
  - `src/utils/text_utils.py` - Enhanced header cleaning patterns and logic
- **Impact**: Chunks now start with relevant content instead of repetitive headers

#### Issue #2: Poor Text Preprocessing During Ingestion
- **Problem**: No text cleaning or noise removal during document processing
- **Solution**:
  - Implemented `clean_document_text()` function that combines header cleaning and normalization
  - Integrated text cleaning into document processing pipeline
  - Added configurable header cleaning via `clean_headers` parameter
- **Files Modified**:
  - `src/utils/text_utils.py` - Added comprehensive text cleaning functions
  - `src/ingestion/document_processor.py` - Integrated cleaning into PDF loading
- **Impact**: All ingested documents are now properly cleaned before chunking

#### Issue #3: Inconsistent Query Performance
- **Problem**: "ec100" worked well but "what is ec200" gave poor results due to stop words diluting BM25 signal
- **Solution**:
  - Added `extract_key_terms()` function to extract course codes and remove stop words
  - Updated `HybridRetriever` to use:
    - Full normalized query for vector search (preserves semantic context)
    - Extracted key terms for BM25 search (focuses on important keywords)
- **Files Modified**:
  - `src/utils/text_utils.py` - Added `extract_key_terms()` function
  - `src/retrieval/hybrid_retriever.py` - Updated to use key term extraction for BM25
- **Impact**: Both short queries ("ec100") and longer queries ("what is ec200") now perform consistently well

#### Issue #4: Missing Document Metadata in Search Results
- **Problem**: Retrieved chunks showed "Source: Unknown" even with high relevance scores due to nested metadata structure in BM25 index
- **Solution**:
  - Flattened metadata structure in BM25 index to match FAISS structure
  - Added `page_start` and `page_end` aliases for compatibility
  - Ensured `source` field is properly preserved at top level in both BM25 and FAISS chunks
- **Files Modified**:
  - `src/ingestion/document_processor.py` - Flattened metadata structure for BM25 chunks
  - `src/ingestion/document_processor.py` - Added page_start/page_end to FAISS metadata
- **Impact**: All chunks now display correct source PDF names and page numbers

### Added

#### Chunk Logging System
- **Feature**: Comprehensive logging of all chunks during ingestion
- **Implementation**:
  - Created `src/utils/logger.py` with logging utilities
  - Added chunk logger that writes to `logs/chunks_loaded.log`
  - Logs chunk ID, source, page, text preview, and metadata for each chunk
  - Logs ingestion start/end and index save events
- **Files Added**:
  - `src/utils/logger.py` - Logging utility module
- **Files Modified**:
  - `src/utils/config.py` - Added `LOG_DIR` and `CHUNK_LOG_FILE` configuration
  - `src/ingestion/document_processor.py` - Integrated chunk logging
  - `scripts/ingest_documents.py` - Enabled chunk logging by default
  - `.gitignore` - Added `logs/` directory to ignore list
- **Usage**: Log file automatically created at `logs/chunks_loaded.log` during ingestion

#### Test Retrieval Script
- **Feature**: Standalone script to test chunk retrieval without starting the API server
- **Implementation**:
  - Created `scripts/test_retrieval.py` for testing retrieval pipeline
  - Tests hybrid retrieval (BM25 + vector search) and reranking
  - Displays detailed results with scores, metadata, and text previews
  - Shows query processing (normalized query and extracted key terms)
- **Files Added**:
  - `scripts/test_retrieval.py` - Retrieval testing script
- **Usage**: 
  ```bash
  python scripts/test_retrieval.py "ec100"
  python scripts/test_retrieval.py "what is ec200"
  ```

### Changed

#### Configuration Updates
- Made `GEMINI_API_KEY` validation conditional (only required when DirectGenerator is used)
- Added logging configuration for chunk tracking
- **Files Modified**:
  - `src/utils/config.py` - Updated GEMINI_API_KEY handling
  - `src/generation/generator.py` - Moved API key validation to generator initialization

### Technical Details

#### Query Processing Flow
1. **Input Query**: User query (e.g., "what is ec200")
2. **Normalization**: `normalize_query()` - trims whitespace, removes multiple spaces
3. **Key Term Extraction**: `extract_key_terms()` - extracts "EC200", removes stop words
4. **Vector Search**: Uses full normalized query for semantic understanding
5. **BM25 Search**: Uses extracted key terms for keyword matching
6. **Hybrid Fusion**: Combines BM25 and vector scores with configurable alpha weight
7. **Reranking**: Cross-encoder reranks results for final relevance

#### Metadata Structure (After Fix)
```python
{
    "chunk_id": "...",
    "text": "...",
    "source": "Btech_Curriculum_2023.pdf",  # Top level (not nested)
    "page": 148,
    "page_start": 148,  # Alias for compatibility
    "page_end": 148,    # Alias for compatibility
    "file_path": "...",
    "chunk_index": 0,
    "ingest_version": "v2"
}
```

### Migration Notes

**Important**: These changes require re-running the ingestion script to take effect:

```bash
python scripts/ingest_documents.py
```

This will:
- Apply improved header/footer cleaning
- Rebuild indices with proper metadata structure
- Ensure all chunks have correct source information
- Generate chunk log file at `logs/chunks_loaded.log`

### Testing

All fixes have been tested and verified:
- OK "ec100" query works correctly (score: 0.9772)
- OK "what is ec100" query works correctly (score: 0.8558)
- OK "what is ec200" query works correctly (score: 0.8815)
- OK All chunks show proper source names (no more "Unknown")
- OK Headers are cleaned from chunk text
- OK Metadata is properly preserved in both BM25 and FAISS indices

---

## Summary of Files Changed

### New Files
- `src/utils/logger.py` - Logging utility
- `scripts/test_retrieval.py` - Retrieval testing script
- `CHANGELOG.md` - This file

### Modified Files
- `src/utils/text_utils.py` - Added key term extraction and enhanced header cleaning
- `src/retrieval/hybrid_retriever.py` - Updated to use key term extraction
- `src/ingestion/document_processor.py` - Fixed metadata structure, integrated cleaning and logging
- `src/utils/config.py` - Added logging configuration, updated GEMINI_API_KEY handling
- `src/generation/generator.py` - Moved API key validation
- `scripts/ingest_documents.py` - Enabled chunk logging
- `.gitignore` - Added logs directory

