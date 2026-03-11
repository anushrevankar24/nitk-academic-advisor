"""Text embedding generation using e5-large-v2."""

import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List
from ..utils.config import EMBEDDING_MODEL, BATCH_SIZE_EMBEDDING


class Embedder:
    """Generate embeddings for text chunks and queries."""
    
    def __init__(self, model_name: str = EMBEDDING_MODEL):
        print(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        print("Embedding model loaded successfully")
    
    def embed_documents(self, texts: List[str], show_progress: bool = True) -> np.ndarray:
        """
        Embed document chunks with passage prefix.
        
        Args:
            texts: List of text chunks
            show_progress: Whether to show progress bar
            
        Returns:
            Numpy array of embeddings (shape: [n_texts, embedding_dim])
        """
        # Add passage prefix for e5 model
        prefixed_texts = [f"passage: {text}" for text in texts]
        
        # Generate embeddings in batches
        embeddings = self.model.encode(
            prefixed_texts,
            batch_size=BATCH_SIZE_EMBEDDING,
            show_progress_bar=show_progress,
            normalize_embeddings=True  # L2 normalization
        )
        
        return embeddings
    
    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed a query with query prefix.
        
        Args:
            query: Query text
            
        Returns:
            Numpy array of embedding (shape: [embedding_dim])
        """
        # Add query prefix for e5 model
        prefixed_query = f"query: {query}"
        
        # Generate embedding
        embedding = self.model.encode(
            prefixed_query,
            normalize_embeddings=True  # L2 normalization
        )
        
        return embedding
    
    def embed_batch(self, texts: List[str], is_query: bool = False) -> np.ndarray:
        """
        Embed a batch of texts.
        
        Args:
            texts: List of texts
            is_query: Whether these are queries (vs documents)
            
        Returns:
            Numpy array of embeddings
        """
        prefix = "query: " if is_query else "passage: "
        prefixed_texts = [f"{prefix}{text}" for text in texts]
        
        embeddings = self.model.encode(
            prefixed_texts,
            batch_size=BATCH_SIZE_EMBEDDING,
            normalize_embeddings=True
        )
        
        return embeddings


