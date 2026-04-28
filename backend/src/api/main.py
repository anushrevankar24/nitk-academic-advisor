"""FastAPI application for NITK Academic Advisor."""

import time
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .models import (
    ChatRequest, ChatResponse, StatusResponse,
    DebugResponse, DebugScores, Source
)
from ..ingestion.embedder import Embedder
from ..retrieval.vector_store import VectorStore
from ..retrieval.bm25_index import BM25Index
from ..retrieval.hybrid_retriever import HybridRetriever
from ..retrieval.mmr import MMRSelector
from ..generation.generator import DirectGenerator
from ..utils.config import (
    BM25_INDEX_FILE, API_HOST, API_PORT, API_RELOAD,
    MIN_CONFIDENCE_THRESHOLD,
    HIGH_CONFIDENCE_THRESHOLD, REQUEST_TIMEOUT, RESPONSE_TIMEOUT,
    HYBRID_ALPHA, TOP_K_HYBRID, FINAL_TOP_K, FINAL_MMR_K,
    PDF_DIR
)
from ..utils.logging_utils import get_api_logger

logger = get_api_logger()

# Initialize FastAPI app
app = FastAPI(
    title="NITK Academic Advisor",
    description="RAG-based question answering for NITK handbooks",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state for models and indices
state = {
    "embedder": None,
    "vector_store": None,
    "bm25_index": None,
    "hybrid_retriever": None,
    "mmr_selector": None,
    "direct_generator": None,
    "ready": False
}


@app.on_event("startup")
async def startup_event():
    """Load models and indices on startup."""
    logger.info("Loading models and indices...")

    try:
        # Load embedder
        logger.info("Loading embedding model...")
        state["embedder"] = Embedder()

        # Load vector store
        logger.info("Loading vector store...")
        state["vector_store"] = VectorStore()

        # Load BM25 index
        logger.info("Loading BM25 index...")
        state["bm25_index"] = BM25Index()
        if BM25_INDEX_FILE.exists():
            state["bm25_index"].load(BM25_INDEX_FILE)
            logger.info(f"BM25 index loaded with {len(state['bm25_index'].chunks)} chunks")
        else:
            logger.warning(f"BM25 index not found at {BM25_INDEX_FILE}")
            logger.warning("Please run the ingestion script first.")

        # Initialize retrieval components
        logger.info("Initializing retrieval components...")
        state["hybrid_retriever"] = HybridRetriever(
            state["vector_store"],
            state["bm25_index"],
            state["embedder"]
        )

        # MMR selector (lightweight — reuses the already-loaded embedder, no new model download)
        state["mmr_selector"] = MMRSelector(state["embedder"])

        # Initialize generation components
        logger.info("Initializing generation components...")
        state["direct_generator"] = DirectGenerator()

        # Check if everything is ready
        if (state["vector_store"].check_health() and
                state["bm25_index"].check_health()):
            state["ready"] = True
            logger.info("OK All systems ready! Server is operational.")
        else:
            logger.warning("WARNING Not all components are ready. Please run ingestion script.")

    except Exception as e:
        logger.error(f"ERROR during startup: {type(e).__name__}: {str(e)}")
        state["ready"] = False
        raise RuntimeError(f"Startup failed: {type(e).__name__}: {str(e)}") from e


@app.get("/")
async def root():
    """Serve the frontend HTML."""
    static_dir = Path(__file__).parent.parent.parent.parent / "frontend" / "dist"
    index_file = static_dir / "index.html"

    if index_file.exists():
        return FileResponse(index_file)
    else:
        return {"message": "NITK Academic Advisor API", "status": "running"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint for question answering.
    Pipeline: Hybrid retrieval → top-K slice → MMR diversity selection → LLM generation.
    The cross-encoder reranker has been removed to reduce memory usage and latency.
    """
    if not state["ready"]:
        raise HTTPException(
            status_code=503,
            detail="System not ready. Please run ingestion script first."
        )

    start_time = time.time()

    try:
        # 1. Hybrid retrieval (BM25 + vector, RRF fusion)
        hybrid_results = state["hybrid_retriever"].retrieve(
            request.question,
            top_k=TOP_K_HYBRID,
            level=request.level
        )

        # 2. Take the top-K candidates (hybrid score already sorts them)
        top_candidates = hybrid_results[:FINAL_TOP_K * 3]  # extra headroom for MMR

        # 3. MMR diversity selection — keeps answers non-redundant
        final_results = state["mmr_selector"].select(
            top_candidates,
            final_k=FINAL_TOP_K,
            lambda_param=0.7
        )

        # 4. Generate answer
        result = state["direct_generator"].generate_answer(
            request.question,
            final_results
        )

        elapsed_ms = (time.time() - start_time) * 1000

        response = ChatResponse(
            answer_markdown=result["answer_markdown"],
            sources=[Source(**s) for s in result["sources"]],
            confidence=result["confidence"],
            time_ms=round(elapsed_ms, 2)
        )

        return response

    except Exception as e:
        logger.error(f"Error in chat endpoint: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate answer. Please try again.")


@app.get("/status", response_model=StatusResponse)
async def status():
    """
    Health check endpoint.
    """
    total_chunks = None
    if state["bm25_index"] and state["bm25_index"].check_health():
        total_chunks = len(state["bm25_index"].chunks)

    return StatusResponse(
        status="ready" if state["ready"] else "not_ready",
        embedding_model_loaded=state["embedder"] is not None,
        vector_store_ready=state["vector_store"] is not None and state["vector_store"].check_health(),
        bm25_index_ready=state["bm25_index"] is not None and state["bm25_index"].check_health(),
        cross_encoder_loaded=False,  # reranker removed
        total_chunks=total_chunks
    )


@app.post("/admin/reindex")
async def reindex(force: bool = False):
    """
    Trigger reindexing (admin endpoint).
    """
    return {
        "message": "Please run the ingestion script to reindex: python scripts/ingest_documents.py",
        "force": force
    }


@app.get("/pdf/{filename}")
async def serve_pdf(filename: str):
    """
    Serve a PDF file from the PDF directory for the in-app viewer.
    Path traversal is prevented by resolving against PDF_DIR.
    """
    safe_name = Path(filename).name
    pdf_path = PDF_DIR / safe_name

    try:
        pdf_path.resolve().relative_to(PDF_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    if not pdf_path.exists() or not pdf_path.is_file():
        raise HTTPException(status_code=404, detail=f"PDF '{safe_name}' not found.")

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=\"{safe_name}\"",
            "X-Frame-Options": "SAMEORIGIN",
        }
    )


@app.get("/debug/topk", response_model=DebugResponse)
async def debug_topk(question: str):
    """
    Debug endpoint to see retrieval scores.
    """
    if not state["ready"]:
        raise HTTPException(
            status_code=503,
            detail="System not ready. Please run ingestion script first."
        )

    try:
        hybrid_results = state["hybrid_retriever"].retrieve(question, top_k=TOP_K_HYBRID)
        top_candidates = hybrid_results[:FINAL_TOP_K * 3]
        mmr_results = state["mmr_selector"].select(top_candidates, final_k=FINAL_MMR_K)
        mmr_chunk_ids = {chunk["chunk_id"] for chunk, _, _ in mmr_results}

        debug_scores = []
        for chunk, score, debug_info in top_candidates:
            debug_scores.append(
                DebugScores(
                    chunk_id=chunk["chunk_id"],
                    text_preview=chunk["text"][:200] + "...",
                    vector_score=debug_info.get("vector_score", 0.0),
                    bm25_score=debug_info.get("bm25_score", 0.0),
                    hybrid_score=debug_info.get("hybrid_score", score),
                    cross_encoder_score=score,
                    mmr_selected=chunk["chunk_id"] in mmr_chunk_ids
                )
            )

        return DebugResponse(
            question=question,
            debug_scores=debug_scores
        )

    except Exception as e:
        logger.error(f"Error in debug endpoint: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="Debug request failed")


# Mount static files
static_dir = Path(__file__).parent.parent.parent.parent / "frontend" / "dist"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")
    
    # Mount everything else (like /vite.svg) normally, but safely handle fallback to root manually or via middleware if needed.
    # Currently just mounting the static dir is fine for simple assets, but for a root app we might need exact paths.
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
