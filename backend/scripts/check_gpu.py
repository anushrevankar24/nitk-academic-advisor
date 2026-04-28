#!/usr/bin/env python3
"""
GPU Detection and System Check Script

This script checks if GPU is available and provides system information.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_gpu():
    """Check GPU availability and system specs."""
    print("=" * 60)
    print("System and GPU Detection")
    print("=" * 60)
    
    # Check PyTorch availability
    try:
        import torch
        print("OK PyTorch is available")
        print(f"   Version: {torch.__version__}")
        
        # Check CUDA availability
        if torch.cuda.is_available():
            print("GPU is available!")
            print(f"   GPU Count: {torch.cuda.device_count()}")
            print(f"   Current GPU: {torch.cuda.current_device()}")
            print(f"   GPU Name: {torch.cuda.get_device_name(0)}")
            print(f"   GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
            print(f"   CUDA Version: {torch.version.cuda}")
            return True
        else:
            print("No GPU detected, will use CPU")
            return False
            
    except ImportError:
        print("ERROR PyTorch not installed")
        return False

def check_embeddings():
    """Check embedding model availability."""
    print("\n" + "=" * 60)
    print("Embedding Model Check")
    print("=" * 60)
    
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        print("OK Using langchain-huggingface")
        return True
    except ImportError as e:
        print(f"ERROR langchain-huggingface not available: {e}")
        print("   Install with: pip install langchain-huggingface")
        return False

def main():
    """Main function."""
    gpu_available = check_gpu()
    embeddings_available = check_embeddings()
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"GPU Available: {'Yes' if gpu_available else 'No'}")
    print(f"Embeddings Available: {'Yes' if embeddings_available else 'No'}")
    
    if gpu_available and embeddings_available:
        print("\nSystem ready for GPU-accelerated processing!")
    elif embeddings_available:
        print("\nSystem ready for CPU processing")
    else:
        print("\nERROR System not ready - missing dependencies")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
