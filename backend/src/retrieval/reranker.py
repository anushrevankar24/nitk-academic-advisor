"""Cross-encoder reranking for accurate relevance scoring."""

from typing import List, Dict, Tuple
from sentence_transformers import CrossEncoder
from ..utils.config import CROSS_ENCODER_MODEL, TOP_K_RERANK


class Reranker:
    """Cross-encoder based reranking."""
    
    def __init__(self, model_name: str = CROSS_ENCODER_MODEL):
        print(f"Loading cross-encoder model: {model_name}")
        self.model = CrossEncoder(model_name)
        print("Cross-encoder model loaded successfully")
    
    def rerank(
        self, 
        query: str, 
        chunks_with_scores: List[Tuple[Dict, float, Dict]], 
        top_k: int = TOP_K_RERANK
    ) -> List[Tuple[Dict, float, Dict]]:
        """
        Rerank chunks using cross-encoder.
        
        Args:
            query: Search query
            chunks_with_scores: List of (chunk, score, debug_scores) tuples
            top_k: Number of top results to return
            
        Returns:
            Reranked list of (chunk, rerank_score, debug_scores) tuples
        """
        if not chunks_with_scores:
            return []
        
        # Extract chunks
        chunks = [item[0] for item in chunks_with_scores]
        
        # Prepare pairs for cross-encoder
        pairs = [[query, chunk["text"]] for chunk in chunks]
        
        # Get cross-encoder scores
        ce_scores = self.model.predict(pairs)
        
        # Combine with original results
        reranked = []
        for i, (chunk, _, debug_scores) in enumerate(chunks_with_scores):
            ce_score = float(ce_scores[i])
            # Update debug scores
            debug_scores["cross_encoder_score"] = ce_score
            reranked.append((chunk, ce_score, debug_scores))
        
        # Sort by cross-encoder score
        reranked.sort(key=lambda x: x[1], reverse=True)
        
        return reranked[:top_k]


