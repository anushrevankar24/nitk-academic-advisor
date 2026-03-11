# Multi-stage Dockerfile for NITK Academic Advisor RAG Chatbot
# Supports both CPU and GPU deployments

# Stage 1: Base image with Python dependencies
FROM python:3.11-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Download NLTK data (required for BM25)
RUN python -c "import nltk; nltk.download('stopwords')"

# Stage 2: Production image
FROM python:3.11-slim

# Install curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /app/data /app/logs && \
    chown -R appuser:appuser /app

WORKDIR /app

# Copy Python packages from base stage
COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base /usr/local/bin /usr/local/bin
COPY --from=base /root/nltk_data /home/appuser/nltk_data

# Copy application code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser scripts/ ./scripts/
COPY --chown=appuser:appuser static/ ./static/
COPY --chown=appuser:appuser example.env ./example.env

# Create necessary directories with correct permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/status || exit 1

# Default command: run the API server
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
