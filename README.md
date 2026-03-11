## NITK Academic Advisor — Retrieval-Augmented QA Chatbot

An intelligent RAG system that answers questions about NITK academic policies and regulations using local handbooks. It combines BM25 keyword search, FAISS vector search, reranking, and Gemini-based answer generation with citations.

### Key Features
- **Hybrid Retrieval**: BM25 lexical + FAISS semantic search
- **Reranking**: Cross-encoder reranker for better relevance
- **Citations**: Each answer returns source PDF and page(s)
- **Modern API + UI**: FastAPI backend with a simple web UI
- **Local artifacts**: Stores indices locally in `data/`

## Architecture Overview
```
User Query
   ↓
Embedding → Vector Search (FAISS)
           + BM25 Keyword Search
   ↓
Score Fusion → Cross-Encoder Rerank
   ↓
Select Top Chunks
   ↓
Gemini (Direct generation using only retrieved chunks)
   ↓
Markdown Answer + Source Citations
```

## Prerequisites
- Python 3.10+
- A Gemini API key
- Optional GPU acceleration (PyTorch + CUDA) for faster embeddings

## Quickstart
1) Clone and enter the project
```bash
git clone https://github.com/anushrevankar24/nitk-academic-advisor.git
cd nitk-academic-advisor
```

2) Create and activate a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

3) Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

GPU optional (recommended if you have CUDA):
```bash
# Choose the correct CUDA version for your system
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

4) Configure environment variables
```bash
cp example.env .env
# Edit .env and set: GEMINI_API_KEY, optional tuning values
```

Minimum required in `.env`:
```
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
```

Other useful variables are already documented in `example.env` (ports, models, chunking, thresholds, paths).

5) Add your PDFs
```
data/pdfs/
  ├─ Btech_Curriculum_2023.pdf
  └─ PG_Curriculum_2023.pdf
```

6) Ingest documents (build vector index + BM25)
```bash
python scripts/ingest_documents.py
```

Expected outputs (under `data/`):
- `bm25_index.pkl` — BM25 index
- `faiss_storage/` — FAISS index + metadata
- `chunks_documents_v2.ndjson` — Chunk dump

7) Run the API server
```bash
# Option A: directly with uvicorn
uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --log-level info

# Option B: via helper script (loads .env, creates venv if needed)
bash start_server.sh
```

Open the UI at:
```
http://localhost:8000
```

## Environment Variables
The project reads configuration via `src/utils/config.py`. Common settings (see `example.env` for defaults):

- API: `API_HOST`, `API_PORT`, `API_RELOAD`
- Gemini: `GEMINI_API_KEY`, `GEMINI_MODEL`
- Chunking: `CHUNK_SIZE`, `CHUNK_OVERLAP`, `INGEST_VERSION`
- Models: `EMBEDDING_MODEL`, `EMBEDDING_DIM`, `CROSS_ENCODER_MODEL`
- Retrieval: `TOP_K_VECTOR`, `TOP_K_BM25`, `TOP_K_HYBRID`, `TOP_K_RERANK`, `FINAL_TOP_K`, `HYBRID_ALPHA`
- MMR (if used elsewhere): `MMR_LAMBDA`
- Paths: `DATA_DIR`, `PDF_DIR`, `CHUNKS_FILE`, `BM25_INDEX_FILE` (FAISS paths are derived)
  - Note: `FINAL_TOP_K` determines how many sources are returned in answers.
- Logging/Timeouts: `LOG_LEVEL`, `REQUEST_TIMEOUT`, `RESPONSE_TIMEOUT`

Copy `example.env` to `.env` and update values as needed.

## API Usage

### Health Check
```bash
curl http://localhost:8000/status
```
Example response:
```json
{
  "status": "ready",
  "embedding_model_loaded": true,
  "vector_store_ready": true,
  "bm25_index_ready": true,
  "cross_encoder_loaded": true,
  "total_chunks": 1234
}
```

### Ask a Question
Endpoint: `POST /chat`
```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the minimum attendance required?"}'
```
Example response:
```json
{
  "answer_markdown": "...",
  "sources": [
    {
      "chunk_id": "chunk_123",
      "text": "...",
      "pdf_name": "Btech_Curriculum_2023.pdf",
      "page_start": 34,
      "page_end": 34,
      "score": 0.92
    }
  ],
  "confidence": 0.87,
  "time_ms": 1234.56
}
```

### Debug Retrieval Scores
Endpoint: `GET /debug/topk?question=...`
```bash
curl "http://localhost:8000/debug/topk?question=attendance%20policy"
```

### Reindex (placeholder)
Endpoint: `POST /admin/reindex`
```bash
curl -X POST http://localhost:8000/admin/reindex
```
Response points you to run the ingestion script instead.

## Frontend UI
Static files live in `static/`. The API serves `static/index.html` at the root path `/`. After starting the server, open:
```
http://localhost:8000
```
and ask a question in the UI. Answers are rendered as markdown with a Sources panel.

## Project Structure
```
nitk-academic-advisor/
├── data/
│   ├── pdfs/                       # Input PDFs (not committed)
│   ├── bm25_index.pkl              # Generated BM25 index
│   ├── chunks_documents_v2.ndjson  # Generated chunks
│   └── faiss_storage/              # FAISS index + metadata
├── scripts/
│   └── ingest_documents.py         # Ingestion pipeline entrypoint
├── src/
│   ├── api/                        # FastAPI app and models
│   ├── generation/                 # Gemini generator
│   ├── ingestion/                  # PDF processing, embeddings
│   ├── retrieval/                  # FAISS, BM25, hybrid, reranker
│   └── utils/                      # Config and helpers
├── static/                         # Frontend assets
├── example.env                     # Env template (copy to .env)
├── requirements.txt
├── start_server.sh                 # Helper to start API
└── README.md
```

## Troubleshooting
- **503 System not ready**: Run `python scripts/ingest_documents.py` to build indices; ensure PDFs exist in `data/pdfs/`.
- **Slow first run**: Model downloads can be ~1GB; subsequent runs are faster.
- **Gemini errors**: Ensure `GEMINI_API_KEY` is set and has quota.
- **Port in use**: Change `API_PORT` in `.env` or kill existing process; `start_server.sh` attempts to free the port.
- **CUDA not used**: Verify your PyTorch install matches your CUDA version.

## Performance Notes
- Embedding step is the heaviest. Use GPU if available for 5-10x speedup.
- Retrieval and generation latency depends on chunk sizes and `TOP_K_*` parameters.

## Security and Data
- Do not commit `.env`, PDFs, or generated indices. Use `example.env` as the template.
- Review `.gitignore` to ensure local artifacts remain untracked.

## License
Educational/Research use.

## Acknowledgments
- Embeddings by `intfloat/e5-base-v2`
- FAISS for vector search
- FastAPI for serving
- Gemini for answer generation

















