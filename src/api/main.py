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
from ..retrieval.reranker import Reranker
from ..retrieval.mmr import MMRSelector
from ..generation.generator import DirectGenerator
from ..utils.config import (
    BM25_INDEX_FILE, API_HOST, API_PORT, API_RELOAD,
    MIN_CONFIDENCE_THRESHOLD,
    HIGH_CONFIDENCE_THRESHOLD, REQUEST_TIMEOUT, RESPONSE_TIMEOUT,
    HYBRID_ALPHA, TOP_K_HYBRID, TOP_K_RERANK, FINAL_TOP_K, FINAL_MMR_K
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
    "reranker": None,
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
        
        state["reranker"] = Reranker()
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


@app.get("/")
async def root():
    """Serve the frontend HTML."""
    static_dir = Path(__file__).parent.parent.parent / "static"
    index_file = static_dir / "index.html"
    
    if index_file.exists():
        return FileResponse(index_file)
    else:
        return {"message": "NITK Academic Advisor API", "status": "running"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint for question answering.
    """
    if not state["ready"]:
        raise HTTPException(
            status_code=503,
            detail="System not ready. Please run ingestion script first."
        )
    
    start_time = time.time()
    
    try:
        # 1. Hybrid retrieval
        hybrid_results = state["hybrid_retriever"].retrieve(
            request.question,
            top_k=TOP_K_HYBRID,
            level=request.level
        )
        
        # 2. Reranking
        reranked_results = state["reranker"].rerank(
            request.question,
            hybrid_results,
            top_k=TOP_K_RERANK
        )
        
        # 3. Select final chunks (MMR for diversity)
        # Use lambda=0.7 to balance relevance (70%) and diversity (30%)
        final_results = state["mmr_selector"].select(
            reranked_results,
            final_k=FINAL_TOP_K,
            lambda_param=0.7
        )
        
        # 4. Generate answer directly from chunks
        result = state["direct_generator"].generate_answer(
            request.question,
            final_results
        )
        
        # Calculate elapsed time
        elapsed_ms = (time.time() - start_time) * 1000
        
        # Build response
        response = ChatResponse(
            answer_markdown=result["answer_markdown"],
            sources=[Source(**s) for s in result["sources"]],
            confidence=result["confidence"],
            time_ms=round(elapsed_ms, 2)
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {type(e).__name__}")
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
        cross_encoder_loaded=state["reranker"] is not None,
        total_chunks=total_chunks
    )


@app.post("/admin/reindex")
async def reindex(force: bool = False):
    """
    Trigger reindexing (admin endpoint).
    """
    # This is a placeholder - actual reindexing should be done via the ingestion script
    return {
        "message": "Please run the ingestion script to reindex: python scripts/ingest_documents.py",
        "force": force
    }


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
        # Get hybrid results
        hybrid_results = state["hybrid_retriever"].retrieve(question, top_k=TOP_K_HYBRID)
        
        # Rerank
        reranked_results = state["reranker"].rerank(question, hybrid_results, top_k=TOP_K_RERANK)
        
        # MMR selection (use configured chunks for debug)
        mmr_results = state["mmr_selector"].select(reranked_results, final_k=FINAL_MMR_K)
        mmr_chunk_ids = {chunk["chunk_id"] for chunk, _, _ in mmr_results}
        
        # Build debug response
        debug_scores = []
        for chunk, score, debug_info in reranked_results:
            debug_scores.append(
                DebugScores(
                    chunk_id=chunk["chunk_id"],
                    text_preview=chunk["text"][:200] + "...",
                    vector_score=debug_info.get("vector_score", 0.0),
                    bm25_score=debug_info.get("bm25_score", 0.0),
                    hybrid_score=debug_info.get("hybrid_score", 0.0),
                    cross_encoder_score=debug_info.get("cross_encoder_score", score),
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
static_dir = Path(__file__).parent.parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
