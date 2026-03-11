#!/bin/bash
# Docker entrypoint script for NITK Academic Advisor

set -e

echo "================================================"
echo "NITK Academic Advisor - Starting up..."
echo "================================================"

# Check if data indices exist
if [ ! -f "/app/data/bm25_index.pkl" ] || [ ! -d "/app/data/faiss_storage" ]; then
    echo "WARNING: Data indices not found!"
    echo ""
    echo "Please run the ingestion script to generate indices:"
    echo "  1. Place PDFs in: data/pdfs/"
    echo "  2. Run: docker exec -it nitk-advisor-api python scripts/ingest_documents.py"
    echo ""
    echo "Or run ingestion locally and mount the data volume."
    echo ""
fi

# Check for GEMINI_API_KEY
if [ -z "$GEMINI_API_KEY" ]; then
    echo "ERROR: GEMINI_API_KEY environment variable is not set!"
    echo "Please set it in your .env file or docker-compose.yml"
    exit 1
fi

echo "Environment configured"
echo "   - API Host: ${API_HOST:-0.0.0.0}"
echo "   - API Port: ${API_PORT:-8000}"
echo "   - Log Level: ${LOG_LEVEL:-INFO}"
echo "   - Gemini Model: ${GEMINI_MODEL:-gemini-2.0-flash-exp}"
echo ""

# Execute the main command
echo "Starting API server..."
exec "$@"
