# NITK Academic Advisor

An intelligent **Retrieval-Augmented Generation (RAG)** chatbot that answers questions about NITK Surathkal's academic regulations, curriculum, grading, attendance, and policies — grounded entirely in the official handbook PDFs.

---

## Features

- **Hybrid Retrieval** — BM25 keyword search + FAISS semantic search, fused with Reciprocal Rank Fusion (RRF)
- **Cross-Encoder Reranking** — `BAAI/bge-reranker-large` reranks candidates for precision
- **MMR Diversity** — Maximal Marginal Relevance selects a diverse final context set for the LLM
- **UG / PG Scope Filtering** — Filter answers strictly to B.Tech or M.Tech/Ph.D curriculum
- **Source Citations** — Every answer links to the exact PDF, page range, and relevance score
- **In-Browser PDF Viewer** — Click any source to open the original PDF at the exact page, with the retrieved text highlighted in yellow
- **React Frontend** — Modern SPA built with React 18 + Vite; markdown rendering, confidence badge, collapsible sources
- **OpenRouter LLM** — Uses Gemini 2.0 Flash (free tier) via OpenRouter; swap models with one env variable

---

## Architecture

```
User Question (React UI)
        │
        ▼
  FastAPI  POST /chat
        │
        ├──► embed_query (E5-base-v2 — query prefix)
        │
        ├──► HybridRetriever
        │       ├── VectorStore.search   (FAISS cosine sim, w/ UG/PG filter)
        │       ├── BM25Index.search     (Okapi BM25, w/ UG/PG filter)
        │       └── RRF Fusion           (alpha=0.3 → top-100)
        │
        ├──► Reranker.rerank             (bge-reranker-large → top-20)
        │
        ├──► MMRSelector.select          (lambda=0.7 → final 10 chunks)
        │
        └──► DirectGenerator
                └── OpenRouter → Gemini 2.0 Flash
                        └── answer_markdown + sources + confidence
```

---

## Prerequisites

- Python 3.10+
- Node.js 18+ (for building the React frontend)
- An **OpenRouter API key** (free at [openrouter.ai](https://openrouter.ai))
- Optional: GPU + CUDA for faster embedding during ingestion

---

## Quickstart

### 1. Clone the repository

```bash
git clone https://github.com/anushrevankar24/nitk-academic-advisor.git
cd nitk-academic-advisor
```

### 2. Create a Python virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **GPU (optional):** Install PyTorch with CUDA for faster embedding during ingestion:
> ```bash
> pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
> ```

### 4. Configure environment variables

```bash
cp example.env .env
# Open .env and set your OPENROUTER_API_KEY
```

The only required value:
```
OPENROUTER_API_KEY="sk-or-..."
```

All other settings have sensible defaults (see `example.env` for the full list with comments).

### 5. Add your PDFs

Place the NITK handbook PDFs in `backend/data/pdfs/`:
```
backend/data/pdfs/
  ├── Btech_Curriculum_2023.pdf
  └── PG_Curriculum_2023.pdf
```

> If you set `BTECH_PDF_URL` and `PG_PDF_URL` in `.env`, the ingestion script will download them automatically.

### 6. Ingest documents

```bash
python backend/scripts/ingest_documents.py
```

This builds:
- `backend/data/faiss_storage/` — FAISS vector index + metadata
- `backend/data/bm25_index.pkl` — BM25 lexical index
- `backend/data/chunks_documents_v2.ndjson` — chunk dump (for inspection)

> **Run once**, or re-run whenever PDFs are updated.

### 7. Build the React frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

The built assets land in `frontend/dist/` and are automatically served by FastAPI.

### 8. Start the server

```bash
bash start_server.sh
```

Or manually:
```bash
export PYTHONPATH="$PWD/backend:$PYTHONPATH"
uvicorn src.api.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open the UI at **http://localhost:8000**

---

## Development Workflow

For active frontend development, use Vite's dev server (with hot-module replacement):

```bash
# Terminal 1 — backend
bash start_server.sh

# Terminal 2 — frontend dev server (proxies /chat /status /pdf to backend)
cd frontend
npm run dev
```

Frontend is available at **http://localhost:5173** during development.

---

## API Reference

### `GET /status` — Health check
```bash
curl http://localhost:8000/status
```
```json
{
  "status": "ready",
  "embedding_model_loaded": true,
  "vector_store_ready": true,
  "bm25_index_ready": true,
  "cross_encoder_loaded": true,
  "total_chunks": 2847
}
```

### `POST /chat` — Ask a question
```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the minimum attendance required?", "level": "ug"}'
```
```json
{
  "answer_markdown": "Students must maintain a minimum attendance of **75%** ...",
  "sources": [
    {
      "chunk_id": "a1b2c3d4...",
      "text": "...raw chunk text...",
      "pdf_name": "Btech_Curriculum_2023.pdf",
      "page_start": 34,
      "page_end": 34,
      "score": 0.91
    }
  ],
  "confidence": 0.88,
  "time_ms": 1432.5
}
```

`level` can be `"ug"`, `"pg"`, or `"both"` (default).

### `GET /debug/topk?question=...` — Inspect retrieval scores
```bash
curl "http://localhost:8000/debug/topk?question=attendance+policy"
```
Returns per-chunk scores: vector, BM25, hybrid (RRF), cross-encoder, MMR selected flag.

### `GET /pdf/{filename}` — Serve a source PDF
Used internally by the in-browser PDF viewer. Secured against path traversal.

### `POST /admin/reindex` — Trigger re-ingestion
Returns a reminder to run `python backend/scripts/ingest_documents.py`.

---

## Environment Variables

All variables are documented in `example.env`. The most important ones:

| Variable | Default | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | *(required)* | Your OpenRouter API key |
| `OPENROUTER_MODEL` | `google/gemini-2.0-flash-exp:free` | LLM model via OpenRouter |
| `EMBEDDING_MODEL` | `intfloat/e5-base-v2` | Sentence embedding model |
| `CROSS_ENCODER_MODEL` | `BAAI/bge-reranker-large` | Reranker model |
| `HYBRID_ALPHA` | `0.3` | BM25 weight (1-alpha = vector weight) |
| `FINAL_TOP_K` | `10` | Final chunks sent to LLM / sources returned |
| `API_PORT` | `8000` | Server port |
| `BTECH_PDF_URL` | *(empty)* | Auto-download URL for B.Tech PDF |
| `PG_PDF_URL` | *(empty)* | Auto-download URL for PG PDF |

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| **503 System not ready** | Run the ingestion script; ensure PDFs exist in `backend/data/pdfs/`. |
| **OpenRouter errors** | Verify `OPENROUTER_API_KEY` is set and valid. Check your OpenRouter dashboard for quota. |
| **Slow first run** | Model downloads (~1–2 GB) happen once; subsequent starts are fast. |
| **Port already in use** | `start_server.sh` kills stale processes automatically. Or change `API_PORT`. |
| **Frontend not loading** | Run `cd frontend && npm run build` to (re)build the React app. |
| **PDF viewer blank** | The PDF must exist in `backend/data/pdfs/` with the exact filename stored in metadata. |

---

## Acknowledgements

- Embeddings: [`intfloat/e5-base-v2`](https://huggingface.co/intfloat/e5-base-v2)
- Reranker: [`BAAI/bge-reranker-large`](https://huggingface.co/BAAI/bge-reranker-large)
- Vector search: [FAISS](https://github.com/facebookresearch/faiss)
- LLM gateway: [OpenRouter](https://openrouter.ai)
- PDF rendering: [PDF.js](https://mozilla.github.io/pdf.js/)
- Framework: [FastAPI](https://fastapi.tiangolo.com/) + [React](https://react.dev/) + [Vite](https://vitejs.dev/)

---

*For educational / research use at NITK Surathkal.*
