#!/bin/bash

# NITK Academic Advisor Server Startup Script
# This script starts the FastAPI application using Gunicorn

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

print_status "Starting NITK Academic Advisor Server..."
print_status "Project directory: $PROJECT_DIR"

# Change to project directory
cd "$PROJECT_DIR"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    print_error "Virtual environment not found. Please run setup first."
    print_status "Creating virtual environment..."
    python3 -m venv .venv
fi

# Load environment variables from .env file
if [ -f ".env" ]; then
    print_status "Loading environment variables from .env file..."
    # Load only simple KEY=VALUE pairs, skip complex values
    while IFS= read -r line; do
        # Skip comments and empty lines
        if [[ "$line" =~ ^[[:space:]]*# ]] || [[ -z "${line// }" ]]; then
            continue
        fi
        # Only export simple KEY=VALUE pairs (no special characters)
        if [[ "$line" =~ ^[A-Z_][A-Z0-9_]*= ]]; then
            export "$line"
        fi
    done < .env
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source .venv/bin/activate

# Skip dependency check - assume they are installed
print_status "Skipping dependency check - assuming requirements are installed"

# Check for environment variables
if [ -z "$GEMINI_API_KEY" ]; then
    print_warning "GEMINI_API_KEY not set. Please check your .env file"
fi

# Check if data files exist
MISSING_ARTIFACTS=0
if [ ! -f "data/bm25_index.pkl" ]; then
    print_error "BM25 index not found. Please run ingestion script first:"
    print_status "python scripts/ingest_documents.py"
    MISSING_ARTIFACTS=1
fi

if [ ! -d "data/faiss_storage" ]; then
    print_error "FAISS storage not found. Please run ingestion script first:"
    print_status "python scripts/ingest_documents.py"
    MISSING_ARTIFACTS=1
fi

if [ "$MISSING_ARTIFACTS" -eq 1 ]; then
    print_error "Required indices missing. Aborting server start."
    exit 1
fi

# Kill any existing processes on the same port
API_PORT=${API_PORT:-8000}
print_status "Checking for existing processes on port $API_PORT..."

# Find and kill existing processes
EXISTING_PID=$(lsof -ti:$API_PORT 2>/dev/null || true)
if [ ! -z "$EXISTING_PID" ]; then
    print_warning "Found existing process on port $API_PORT (PID: $EXISTING_PID). Killing it..."
    kill -9 $EXISTING_PID 2>/dev/null || true
    sleep 2
fi

# Set default environment variables if not set
export API_HOST=${API_HOST:-"127.0.0.1"}
export API_PORT=${API_PORT:-8000}
# Convert LOG_LEVEL to lowercase for uvicorn compatibility
LOG_LEVEL_LOWER=$(echo "${LOG_LEVEL:-warning}" | tr '[:upper:]' '[:lower:]')
export GUNICORN_WORKERS=${GUNICORN_WORKERS:-1}
export GUNICORN_TIMEOUT=${GUNICORN_TIMEOUT:-120}

print_status "Starting server..."
print_success "Server will be available at: http://$API_HOST:$API_PORT"

# Start the server
print_status "Loading models and starting server..."
print_status "Using Uvicorn for optimal performance..."

# Use Uvicorn for optimal performance
exec uvicorn src.api.main:app \
    --host $API_HOST \
    --port $API_PORT \
    --log-level $LOG_LEVEL_LOWER
