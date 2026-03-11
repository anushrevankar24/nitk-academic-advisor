"""Maximal Marginal Relevance (MMR) for diversity-aware selection."""

import numpy as np
from typing import List, Dict, Tuple
from ..utils.config import FINAL_MMR_K, MMR_LAMBDA


class MMRSelector:
    """Select diverse chunks using MMR algorithm."""
    
    def __init__(self, embedder):
        self.embedder = embedder
    
    def select(
        self,
        chunks_with_scores: List[Tuple[Dict, float, Dict]],
        final_k: int = FINAL_MMR_K,
        lambda_param: float = MMR_LAMBDA
    ) -> List[Tuple[Dict, float, Dict]]:
        """
        Select diverse chunks using MMR.
        
        Args:
            chunks_with_scores: List of (chunk, score, debug_scores) tuples
            final_k: Number of final chunks to select
            lambda_param: Trade-off between relevance (high) and diversity (low)
            
        Returns:
            Selected chunks with scores
        """
        if len(chunks_with_scores) <= final_k:
            return chunks_with_scores
        
        # Extract chunks and relevance scores
        chunks = [item[0] for item in chunks_with_scores]
        relevance_scores = np.array([item[1] for item in chunks_with_scores])
        
        # Embed all chunks for similarity calculation
        chunk_texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedder.embed_documents(chunk_texts, show_progress=False)
        
        # Initialize
        selected_indices = []
        remaining_indices = list(range(len(chunks)))
        
        # Select first chunk (highest relevance)
        first_idx = remaining_indices[0]
        selected_indices.append(first_idx)
        remaining_indices.remove(first_idx)
        
        # Select remaining chunks using MMR
        while len(selected_indices) < final_k and remaining_indices:
            mmr_scores = []
            
            for idx in remaining_indices:
                # Relevance score (normalized)
                relevance = relevance_scores[idx]
                
                # Similarity to already selected chunks
                similarities = []
                for selected_idx in selected_indices:
                    sim = self._cosine_similarity(
                        embeddings[idx], 
                        embeddings[selected_idx]
                    )
                    similarities.append(sim)
                
                max_similarity = max(similarities) if similarities else 0
                
                # MMR score: lambda * relevance - (1-lambda) * max_similarity
                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_similarity
                mmr_scores.append((idx, mmr_score))
            
            # Select chunk with highest MMR score
            best_idx = max(mmr_scores, key=lambda x: x[1])[0]
            selected_indices.append(best_idx)
            remaining_indices.remove(best_idx)
        
        # Return selected chunks
        selected = [chunks_with_scores[idx] for idx in selected_indices]
        
        return selected
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Compute cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity
        """
        # Vectors are already L2-normalized from embedder
        return float(np.dot(vec1, vec2))


