"""Pydantic models for API requests and responses."""

from typing import List, Optional, Literal
from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    question: str
    level: Literal["ug", "pg", "both"] = "both"


class Source(BaseModel):
    """Source document information."""
    chunk_id: str
    text: str = ""  # Make text optional with default
    pdf_name: str
    page_start: int
    page_end: int
    score: float


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    answer_markdown: str
    sources: List[Source]
    confidence: float
    time_ms: float


class StatusResponse(BaseModel):
    """Response model for status endpoint."""
    status: str
    embedding_model_loaded: bool
    vector_store_ready: bool
    bm25_index_ready: bool
    cross_encoder_loaded: bool
    total_chunks: Optional[int] = None


class DebugScores(BaseModel):
    """Debug scores for a chunk."""
    chunk_id: str
    text_preview: str
    vector_score: float
    bm25_score: float
    hybrid_score: float
    cross_encoder_score: float
    mmr_selected: bool


class DebugResponse(BaseModel):
    """Response model for debug endpoint."""
    question: str
    debug_scores: List[DebugScores]
