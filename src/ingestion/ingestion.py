"""
Document processing pipeline for academic PDFs.

This module provides a clean, reliable setup using semantic chunking
for academic PDFs with e5-base-v2 embeddings and GPU optimization.
"""

import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from tqdm import tqdm

# Document processing imports
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_experimental.text_splitter import SemanticChunker
from langchain.schema import Document

# Use the new HuggingFaceEmbeddings from langchain-huggingface
from langchain_huggingface import HuggingFaceEmbeddings

# FAISS
import faiss
import pickle
import numpy as np

# Configuration
from ..utils.config import PDF_DIR, DATA_DIR, INGEST_VERSION


class DocumentProcessor:
    """
    Document processing pipeline for academic PDFs.
    
    Features:
    - Semantic chunking with sensible parameters for academic PDFs
    - e5-base-v2 embeddings with GPU optimization
    - Clean, reliable setup
    - Built-in BM25 index creation for hybrid retrieval
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        embedding_model: str = "intfloat/e5-base-v2",
        device: str = "auto"  # Will auto-detect GPU if available
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_model_name = embedding_model
        
        # Auto-detect device if needed
        if device == "auto":
            try:
                import torch
                if torch.cuda.is_available():
                    device = "cuda"
                    print(f"GPU detected: {torch.cuda.get_device_name(0)}")
                    print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
                else:
                    device = "cpu"
                    print("No GPU detected, using CPU")
            except ImportError:
                device = "cpu"
                print("PyTorch not available, using CPU")
        
        print(f"Using device: {device}")
        
        # Initialize semantic chunker
        self.text_splitter = SemanticChunker(
            embeddings=HuggingFaceEmbeddings(
                model_name=embedding_model,
                model_kwargs={"device": device}
            ),
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=95,
            buffer_size=3  # Number of sentences to consider for merging
        )
        
        # Initialize embeddings for processing
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={"device": device}
        )
        
        print(f"Initialized document processor with {embedding_model}")
        print(f"Chunk size: {chunk_size}, Overlap: {chunk_overlap}")
        print(f"Device: {device}")
    
    def load_pdfs(self, pdf_dir: Path) -> List[Document]:
        """
        Load all PDFs from directory using PyMuPDFLoader.
        
        Args:
            pdf_dir: Directory containing PDF files
            
        Returns:
            List of Document objects
        """
        documents = []
        pdf_files = list(pdf_dir.glob("*.pdf"))
        
        if not pdf_files:
            raise ValueError(f"No PDF files found in {pdf_dir}")
        
        print(f"Found {len(pdf_files)} PDF files")
        
        for pdf_path in tqdm(pdf_files, desc="Loading PDFs"):
            try:
                loader = PyMuPDFLoader(str(pdf_path))
                docs = loader.load()
                
                # Add metadata to each document
                for doc in docs:
                    doc_level = "general"
                    if "Btech" in pdf_path.name:
                        doc_level = "ug"
                    elif "PG" in pdf_path.name:
                        doc_level = "pg"

                    doc.metadata.update({
                        "source": pdf_path.name,
                        "file_path": str(pdf_path),
                        "doc_level": doc_level
                    })
                
                documents.extend(docs)
                print(f"  Loaded {len(docs)} pages from {pdf_path.name}")
                
            except Exception as e:
                print(f"Error loading {pdf_path}: {e}")
                continue
        
        print(f"Total documents loaded: {len(documents)}")
        return documents
    
    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """
        Chunk documents using semantic chunking.
        
        Args:
            documents: List of Document objects
            
        Returns:
            List of chunked Document objects
        """
        print("Chunking documents with semantic chunker...")
        
        all_chunks = []
        
        for doc in tqdm(documents, desc="Chunking documents"):
            try:
                chunks = self.text_splitter.split_documents([doc])
                
                # Add chunk metadata
                for i, chunk in enumerate(chunks):
                    chunk.metadata.update({
                        "chunk_id": self._generate_chunk_id(
                            doc.metadata.get("source", "unknown"),
                            doc.metadata.get("page", 0),
                            i
                        ),
                        "ingest_version": INGEST_VERSION,
                        "chunk_index": i
                    })
                
                all_chunks.extend(chunks)
                
            except Exception as e:
                print(f"Error chunking document {doc.metadata.get('source', 'unknown')}: {e}")
                continue
        
        print(f"Created {len(all_chunks)} chunks")
        return all_chunks
    
    def generate_embeddings(self, chunks: List[Document]) -> List[List[float]]:
        """
        Generate embeddings for document chunks.
        
        Args:
            chunks: List of chunked Document objects
            
        Returns:
            List of embedding vectors
        """
        print("Generating embeddings...")
        
        texts = [chunk.page_content for chunk in chunks]
        embeddings = self.embeddings.embed_documents(texts)
        
        print(f"Generated {len(embeddings)} embeddings")
        return embeddings
    
    def save_to_faiss(
        self, 
        chunks: List[Document], 
        embeddings: List[List[float]], 
        index_name: str = "documents_v2"
    ) -> None:
        """
        Save chunks and embeddings to FAISS.
        
        Args:
            chunks: List of chunked Document objects
            embeddings: List of embedding vectors
            index_name: Name of the FAISS index
        """
        print(f"Saving to FAISS index: {index_name}")
        
        # Setup FAISS index
        faiss_path = DATA_DIR / "faiss_storage"
        faiss_path.mkdir(parents=True, exist_ok=True)
        
        index_file = faiss_path / f"{index_name}_index.bin"
        metadata_file = faiss_path / f"{index_name}_metadata.pkl"
        
        # Create FAISS index
        embedding_dim = len(embeddings[0]) if embeddings else 768
        index = faiss.IndexFlatIP(embedding_dim)  # Inner product for cosine similarity
        
        # Convert embeddings to numpy array and normalize
        embeddings_array = np.array(embeddings, dtype='float32')
        faiss.normalize_L2(embeddings_array)
        
        # Add embeddings to index
        index.add(embeddings_array)
        
        # Prepare metadata - preserve all important fields
        metadata = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = {
                "chunk_id": chunk.metadata.get("chunk_id", f"chunk_{i}"),
                "text": chunk.page_content,
                "source": chunk.metadata.get("source", "unknown"),
                "file_path": chunk.metadata.get("file_path", ""),
                "page": chunk.metadata.get("page", 0),
                "chunk_index": chunk.metadata.get("chunk_index", i),
                "ingest_version": chunk.metadata.get("ingest_version", INGEST_VERSION),
                # Preserve additional metadata that might be useful
                "original_length": chunk.metadata.get("original_length", 0),
                "cleaned_length": chunk.metadata.get("cleaned_length", 0),
                "headers_cleaned": chunk.metadata.get("headers_cleaned", False)
            }
            metadata.append(chunk_metadata)
        
        # Save index and metadata
        try:
            faiss.write_index(index, str(index_file))
            with open(metadata_file, 'wb') as f:
                pickle.dump(metadata, f)
            print(f"Saved FAISS index to {index_file}")
            print(f"Saved metadata to {metadata_file}")
        except Exception as e:
            print(f"Error saving FAISS index: {e}")
            raise
        
        print(f"Successfully saved {len(chunks)} chunks to FAISS")
    
    def save_chunks_to_file(self, chunks: List[Document], output_file: Path) -> None:
        """
        Save chunks to NDJSON file for backup/debugging.
        
        Args:
            chunks: List of chunked Document objects
            output_file: Path to output file
        """
        print(f"Saving chunks to {output_file}")
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for chunk in tqdm(chunks, desc="Saving chunks"):
                chunk_data = {
                    "chunk_id": chunk.metadata.get("chunk_id", ""),
                    "text": chunk.page_content,
                    "metadata": chunk.metadata
                }
                f.write(json.dumps(chunk_data, ensure_ascii=False) + '\n')
        
        print(f"Saved {len(chunks)} chunks to {output_file}")
    
    def _generate_chunk_id(self, source: str, page: int, chunk_index: int) -> str:
        """Generate deterministic chunk ID."""
        id_string = f"{source}_{page}_{chunk_index}"
        return hashlib.md5(id_string.encode()).hexdigest()
    
    def process_pdfs(self, pdf_dir: Path, output_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Complete PDF processing pipeline.
        
        Args:
            pdf_dir: Directory containing PDF files
            output_dir: Optional output directory for chunks file
            
        Returns:
            Dictionary with processing results
        """
        if output_dir is None:
            output_dir = DATA_DIR
        
        print("=" * 60)
        print("Document Processing Pipeline")
        print("=" * 60)
        
        # 1. Load PDFs
        print("\n[1/5] Loading PDFs...")
        documents = self.load_pdfs(pdf_dir)
        
        # 2. Chunk documents
        print("\n[2/5] Chunking documents...")
        chunks = self.chunk_documents(documents)
        
        # 3. Generate embeddings
        print("\n[3/5] Generating embeddings...")
        embeddings = self.generate_embeddings(chunks)
        
        # 4. Save to FAISS
        print("\n[4/5] Saving to FAISS...")
        self.save_to_faiss(chunks, embeddings)
        
        # Save chunks to file for backup
        chunks_file = output_dir / "chunks_documents_v2.ndjson"
        self.save_chunks_to_file(chunks, chunks_file)
        
        # Build BM25 index
        print("\n[5/5] Building BM25 index...")
        from ..retrieval.bm25_index import BM25Index
        from ..utils.config import BM25_INDEX_FILE
        
        # Convert Document objects to dictionaries for BM25
        chunk_dicts = []
        for chunk in chunks:
            chunk_dict = {
                "chunk_id": chunk.metadata.get("chunk_id", ""),
                "text": chunk.page_content,
                "metadata": chunk.metadata
            }
            chunk_dicts.append(chunk_dict)
        
        bm25_index = BM25Index()
        bm25_index.build_index(chunk_dicts)
        bm25_index.save(BM25_INDEX_FILE)
        print(f"BM25 index built and saved to {BM25_INDEX_FILE}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("Processing Complete!")
        print("=" * 60)
        print(f"Total pages: {len(documents)}")
        print(f"Total chunks: {len(chunks)}")
        print(f"Chunks file: {chunks_file}")
        print(f"FAISS storage: {DATA_DIR / 'faiss_storage'}")
        print(f"BM25 index: {BM25_INDEX_FILE}")
        print("=" * 60)
        
        return {
            "documents": len(documents),
            "chunks": len(chunks),
            "chunks_file": str(chunks_file),
            "faiss_path": str(DATA_DIR / "faiss_storage"),
            "bm25_index": str(BM25_INDEX_FILE)
        }
