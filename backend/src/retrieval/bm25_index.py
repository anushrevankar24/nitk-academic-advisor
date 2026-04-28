"""In-memory BM25 index using rank-bm25."""

import pickle
from pathlib import Path
from typing import List, Dict, Tuple
from rank_bm25 import BM25Okapi
import re
from ..utils.config import TOP_K_BM25
import nltk
from nltk.corpus import stopwords

nltk.download('stopwords')


class BM25Index:
    """BM25 keyword search index."""
    
    # Cache stopwords set (avoid re-computing on every _tokenize call)
    _stop_words = set(stopwords.words('english'))

    def __init__(self):
        self.index = None
        self.chunks = []
        self.chunk_id_to_idx = {}

    def build_index(self, chunks: List[Dict]):
        """
        Build BM25 index from chunks.

        Args:
            chunks: List of chunk dictionaries
        """
        self.chunks = chunks

        # Create chunk_id to index mapping
        self.chunk_id_to_idx = {
            chunk["chunk_id"]: i for i, chunk in enumerate(chunks)
        }

        # Tokenize all chunk texts
        tokenized_chunks = [self._tokenize(chunk["text"]) for chunk in chunks]

        # Build BM25 index
        self.index = BM25Okapi(tokenized_chunks)

        print(f"Built BM25 index with {len(chunks)} chunks")

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text for BM25.
        Preserves numbers and important punctuation.
        Removes stopwords for better term matching.

        Args:
            text: Text to tokenize

        Returns:
            List of tokens
        """
        # Convert to lowercase
        text = text.lower()

        # Split on whitespace and common punctuation, but preserve numbers
        # Keep alphanumeric tokens and numbers with decimals/dots
        tokens = re.findall(r'\b\w+(?:\.\w+)*\b', text)

        # Remove stopwords (consistent with query-time filtering)
        tokens = [t for t in tokens if t not in self._stop_words]

        return tokens

    def search(self,
        query: str,
        top_k: int = TOP_K_BM25,
        filter_fn: callable = None
    ) -> List[Tuple[Dict, float]]:
        """
        Search using BM25.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of (chunk_dict, score) tuples
        """
        if not self.index:
            raise ValueError("Index not built. Call build_index() first.")

        # Tokenize query (stopwords removed by _tokenize)
        tokenized_query = self._tokenize(query)

        # Get BM25 scores
        scores = self.index.get_scores(tokenized_query)

        # Get top k indices (fetch more if filtering)
        # If filtering, we need to fetch more candidates to ensure we get enough valid results
        fetch_k = top_k * 3 if filter_fn else top_k
        top_indices = scores.argsort()[-fetch_k:][::-1]

        # Return chunks with scores
        results = []
        for idx in top_indices:
            chunk = self.chunks[idx]
            
            if filter_fn and not filter_fn(chunk):
                continue
            
            score = float(scores[idx])
            results.append((chunk, score))
            
            if len(results) >= top_k:
                break

        return results


    def save(self, filepath: Path):
        """
        Save BM25 index to disk.

        Args:
            filepath: Path to save the index
        """
        data = {
            "index": self.index,
            "chunks": self.chunks,
            "chunk_id_to_idx": self.chunk_id_to_idx
        }

        with open(filepath, 'wb') as f:
            pickle.dump(data, f)

        print(f"Saved BM25 index to {filepath}")

    def load(self, filepath: Path):
        """
        Load BM25 index from disk.

        Args:
            filepath: Path to load the index from
        """
        with open(filepath, 'rb') as f:
            data = pickle.load(f)

        self.index = data["index"]
        self.chunks = data["chunks"]
        self.chunk_id_to_idx = data["chunk_id_to_idx"]

        print(f"Loaded BM25 index from {filepath} with {len(self.chunks)} chunks")

    def check_health(self) -> bool:
        """
        Check if index is loaded and ready.

        Returns:
            True if index is ready
        """
        return self.index is not None and len(self.chunks) > 0
