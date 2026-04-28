"""FAISS vector store wrapper for local storage."""

import numpy as np
import pickle
import faiss
from typing import List, Dict, Tuple
from tqdm import tqdm
from pathlib import Path
from ..utils.config import (
    FAISS_INDEX_FILE, FAISS_METADATA_FILE,
    EMBEDDING_DIM, TOP_K_VECTOR
)


class VectorStore:
    """FAISS vector store for chunk embeddings."""
    
    def __init__(self):
        print(f"Initializing FAISS vector store")
        self.index = None
        self.metadata = []
        self.index_file = FAISS_INDEX_FILE
        self.metadata_file = FAISS_METADATA_FILE
        self._load_index()
    
    def _load_index(self):
        """Load existing FAISS index and metadata if available."""
        if self.index_file.exists() and self.metadata_file.exists():
            try:
                print(f"Loading existing FAISS index from {self.index_file}")
                self.index = faiss.read_index(str(self.index_file))
                
                with open(self.metadata_file, 'rb') as f:
                    self.metadata = pickle.load(f)
                
                print(f"Loaded FAISS index with {self.index.ntotal} vectors")
            except Exception as e:
                print(f"Error loading FAISS index: {e}")
                self._create_new_index()
        else:
            print("No existing FAISS index found, will create new one")
            self._create_new_index()
    
    def _create_new_index(self):
        """Create a new FAISS index."""
        print(f"Creating new FAISS index with dimension {EMBEDDING_DIM}")
        self.index = faiss.IndexFlatIP(EMBEDDING_DIM)  # Inner product for cosine similarity
        self.metadata = []
    
    def create_index(self, recreate: bool = False):
        """
        Create or recreate the FAISS index.
        
        Args:
            recreate: If True, delete existing index first
        """
        if recreate:
            if self.index_file.exists():
                self.index_file.unlink()
            if self.metadata_file.exists():
                self.metadata_file.unlink()
            print("Deleted existing FAISS index")
        
        self._create_new_index()
        print("Created new FAISS index")
    
    def upsert_chunks(
        self, 
        chunks: List[Dict], 
        embeddings: np.ndarray,
        batch_size: int = 100
    ):
        """
        Upsert chunks with embeddings to FAISS.
        
        Args:
            chunks: List of chunk dictionaries
            embeddings: Numpy array of embeddings
            batch_size: Batch size for upserting
        """
        print(f"Upserting {len(chunks)} chunks to FAISS")
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Add to FAISS index
        self.index.add(embeddings.astype('float32'))
        
        # Store metadata - preserve all fields from chunk
        for i, chunk in enumerate(chunks):
            # Start with basic required fields
            metadata = {
                "chunk_id": chunk.get("chunk_id", f"chunk_{i}"),
                "text": chunk.get("text", ""),
                "source": chunk.get("source", "unknown"),
                "file_path": chunk.get("file_path", ""),
                "page": chunk.get("page", 0),
                "chunk_index": chunk.get("chunk_index", i),
                "ingest_version": chunk.get("ingest_version", "v2")
            }
            
            # Add any additional metadata fields that exist
            for key, value in chunk.items():
                if key not in metadata and key not in ["chunk_id", "text"]:  # Avoid overwriting core fields
                    metadata[key] = value
            
            self.metadata.append(metadata)
        
        # Save index and metadata
        self._save_index()
        
        print(f"Upserted {len(chunks)} chunks to FAISS")
    
    def _save_index(self):
        """Save FAISS index and metadata to disk."""
        try:
            # Ensure directory exists
            self.index_file.parent.mkdir(parents=True, exist_ok=True)
            self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save FAISS index
            faiss.write_index(self.index, str(self.index_file))
            
            # Save metadata
            with open(self.metadata_file, 'wb') as f:
                pickle.dump(self.metadata, f)
            
            print(f"Saved FAISS index to {self.index_file}")
            print(f"Saved metadata to {self.metadata_file}")
            
        except Exception as e:
            print(f"Error saving FAISS index: {e}")
    
    def search(
        self, 
        query_vector: np.ndarray, 
        top_k: int = TOP_K_VECTOR,
        score_threshold: float = None,
        filter_fn: callable = None
    ) -> List[Tuple[Dict, float]]:
        """
        Search for similar chunks.
        
        Args:
            query_vector: Query embedding
            top_k: Number of results to return
            score_threshold: Minimum similarity score
            
        Returns:
            List of (chunk_dict, score) tuples
        """
        if self.index is None or self.index.ntotal == 0:
            print("FAISS index is empty or not loaded")
            return []
        
        # Normalize query vector for cosine similarity
        query_vector = query_vector.reshape(1, -1).astype('float32')
        faiss.normalize_L2(query_vector)
        
        # Over-fetch when filtering to ensure we get enough results after filtering
        fetch_k = top_k * 3 if filter_fn else top_k
        
        # Search
        scores, indices = self.index.search(query_vector, min(fetch_k, self.index.ntotal))
        
        # Convert to (chunk, score) tuples
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # Invalid index
                continue
                
            if score_threshold and score < score_threshold:
                continue
                
            
            chunk_metadata = self.metadata[idx]
            
            if filter_fn and not filter_fn(chunk_metadata):
                continue
                
            results.append((chunk_metadata, float(score)))
            
            # Stop once we have enough results (important when over-fetching)
            if len(results) >= top_k:
                break
        
        return results

    
    def get_index_info(self) -> Dict:
        """
        Get information about the FAISS index.
        
        Returns:
            Dictionary with index stats
        """
        if self.index is None:
            return {
                "total_vectors": 0,
                "dimension": EMBEDDING_DIM,
                "index_type": "None"
            }
        
        return {
            "total_vectors": self.index.ntotal,
            "dimension": self.index.d,
            "index_type": "FAISS IndexFlatIP",
            "is_trained": self.index.is_trained
        }
    
    def check_health(self) -> bool:
        """
        Check if the vector store is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            if self.index is None:
                return False
            
            if self.index.ntotal == 0:
                return False
            
            # Try a simple search
            test_vector = np.random.rand(1, EMBEDDING_DIM).astype('float32')
            faiss.normalize_L2(test_vector)
            self.index.search(test_vector, 1)
            
            return True
            
        except Exception as e:
            print(f"FAISS health check failed: {e}")
            return False