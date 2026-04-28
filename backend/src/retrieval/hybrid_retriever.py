"""Hybrid retrieval combining BM25 and vector search."""

from typing import List, Dict, Tuple
from ..utils.config import (
    TOP_K_VECTOR, TOP_K_BM25, TOP_K_HYBRID, HYBRID_ALPHA
)
from ..utils.text_utils import normalize_query, extract_key_terms


class HybridRetriever:
    """Combine BM25 and vector search with score fusion."""
    
    def __init__(self, vector_store, bm25_index, embedder):
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self.embedder = embedder
    
    def retrieve(
        self, 
        query: str, 
        top_k: int = TOP_K_HYBRID,
        alpha: float = HYBRID_ALPHA,
        level: str = "both"
    ) -> List[Tuple[Dict, float, Dict]]:
        """
        Hybrid retrieval combining BM25 and vector search.
        
        Args:
            query: Search query
            top_k: Number of results to return
            alpha: Weight for BM25 (1-alpha for vector)
            
        Returns:
            List of (chunk_dict, hybrid_score, debug_scores) tuples
        """
        # Normalize query for vector search (preserves semantic context)
        normalized_query = normalize_query(query)
        
        # Extract key terms for BM25 search (focuses on important keywords)
        bm25_query = extract_key_terms(query)
        
        # Define filter function based on level
        filter_fn = None
        if level == "ug":
            filter_fn = lambda m: m.get("doc_level") == "ug"
        elif level == "pg":
            filter_fn = lambda m: m.get("doc_level") == "pg"
        # If level is "both" or anything else, no filter is applied
        
        # 1. Vector search (use full normalized query for semantic understanding)
        query_embedding = self.embedder.embed_query(normalized_query)
        vector_results = self.vector_store.search(
            query_embedding, 
            top_k=TOP_K_VECTOR,
            filter_fn=filter_fn
        )
        
        # 2. BM25 search (use key terms for better keyword matching)
        bm25_results = self.bm25_index.search(
            bm25_query, 
            top_k=TOP_K_BM25,
            filter_fn=filter_fn
        )
        
        # 3. Merge results by chunk_id
        chunk_scores = {}  # chunk_id -> {chunk, vector_score, bm25_score}
        
        for chunk, score in vector_results:
            chunk_id = chunk["chunk_id"]
            chunk_scores[chunk_id] = {
                "chunk": chunk,
                "vector_score": score,
                "bm25_score": 0.0
            }
        
        for chunk, score in bm25_results:
            chunk_id = chunk["chunk_id"]
            if chunk_id in chunk_scores:
                chunk_scores[chunk_id]["bm25_score"] = score
            else:
                chunk_scores[chunk_id] = {
                    "chunk": chunk,
                    "vector_score": 0.0,
                    "bm25_score": score
                }
        
        # 4. Compute RRF scores from rank positions
        # Sort each result list by score to get ranks
        vector_ranked = sorted(chunk_scores.items(), key=lambda x: x[1]["vector_score"], reverse=True)
        bm25_ranked = sorted(chunk_scores.items(), key=lambda x: x[1]["bm25_score"], reverse=True)
        
        # Assign RRF scores based on rank (k=60 is standard)
        rrf_k = 60
        vector_rrf = {chunk_id: 1.0 / (rrf_k + rank + 1) for rank, (chunk_id, _) in enumerate(vector_ranked)}
        bm25_rrf = {chunk_id: 1.0 / (rrf_k + rank + 1) for rank, (chunk_id, _) in enumerate(bm25_ranked)}
        
        # 5. Compute hybrid scores using weighted RRF
        results = []
        for chunk_id, scores in chunk_scores.items():
            hybrid_score = (
                alpha * bm25_rrf[chunk_id] + 
                (1 - alpha) * vector_rrf[chunk_id]
            )
            
            debug_scores = {
                "vector_score": scores["vector_score"],
                "bm25_score": scores["bm25_score"],
                "vector_rrf": vector_rrf[chunk_id],
                "bm25_rrf": bm25_rrf[chunk_id],
                "hybrid_score": hybrid_score
            }
            
            results.append((scores["chunk"], hybrid_score, debug_scores))
        
        # 6. Sort by hybrid score and return top k
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:top_k]
    
    @staticmethod
    def _rrf_score(rank: int, k: int = 60) -> float:
        """
        Reciprocal Rank Fusion score.
        
        Args:
            rank: 0-indexed rank position
            k: Smoothing constant (standard: 60)
            
        Returns:
            RRF score
        """
        return 1.0 / (k + rank + 1)


