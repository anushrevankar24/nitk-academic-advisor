"""Test script for BM25 search functionality."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.retrieval.bm25_index import BM25Index
from src.utils.config import BM25_INDEX_FILE

def test_bm25_search():
    """Test BM25 search with different queries."""
    print("\nInitializing BM25 Index...")
    bm25_index = BM25Index()

    # Load existing index
    if BM25_INDEX_FILE.exists():
        print(f"Loading BM25 index from {BM25_INDEX_FILE}")
        bm25_index.load(BM25_INDEX_FILE)
        print(f"Loaded {len(bm25_index.chunks)} chunks")
    else:
        print(f"ERROR: BM25 index not found at {BM25_INDEX_FILE}")
        print("Please run the ingestion script first.")
        sys.exit(1)

    # Test queries
    test_queries = [
        "What is the attendance requirement?",
        "How do I apply for a hostel room?",
        "What are the course registration dates?",
        "Tell me about examination rules",
        "How do I calculate my CGPA?"
    ]

    TOP_K = 5  # Number of results to show for each query

    print("\nTesting BM25 Search:")
    print("-" * 80)

    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 40)

        # Perform BM25 search
        results = bm25_index.search(query, top_k=TOP_K)

        # Print results
        for i, (chunk, score) in enumerate(results, 1):
            print(f"\nResult {i} (Score: {score:.3f}):")
            print(f"Source: {chunk.get('source', 'Unknown')} - Page {chunk.get('page', 'Unknown')}")
            print(f"Text: {chunk['text'][:200]}...")  # Show first 200 chars

        print("-" * 80)

if __name__ == "__main__":
    test_bm25_search()
