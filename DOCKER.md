# Docker Deployment Guide

## Quick Start (CPU)

### First Time Setup

1. **Create `.env` file**:
```bash
cp example.env .env
# Edit .env and set your GEMINI_API_KEY
nano .env  # or vim/code/etc.
```

2. **Place your PDFs**:
```bash
mkdir -p data/pdfs
# Copy your handbook PDF files into data/pdfs/
```

3. **Run ingestion LOCALLY** (recommended - faster and see progress):
```bash
# Activate your virtual environment
source .venv/bin/activate  # or: python -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run ingestion (takes 1-2 hours on CPU)
python scripts/ingest_documents.py
```

**OR** run ingestion in Docker (slower, no progress output):
```bash
# Build image first
docker compose build

# Run ingestion (will take 1-2 hours, runs in background)
docker compose run --rm nitk-advisor python scripts/ingest_documents.py

# Note: You won't see real-time progress. Check with:
# docker compose logs -f
```

### Starting the Server

4. **Build and start the API service**:
```bash
# Build image (if not already built)
docker compose build

# Start the service in background
docker compose up -d
```

5. **Verify it's running**:
```bash
# Check container status (should show "healthy" after ~30 seconds)
docker compose ps

# Check API status
curl http://localhost:8000/status
```

6. **Access the application**:
- Web UI: http://localhost:8000
- API docs: http://localhost:8000/docs

## GPU Deployment

For faster embeddings and processing:

1. **Install NVIDIA Docker runtime**:
```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

2. **Build and run GPU version**:
```bash
docker compose -f docker-compose.gpu.yml build
docker compose -f docker-compose.gpu.yml up -d
```

3. **Verify GPU is detected**:
```bash
docker exec -it nitk-advisor-api-gpu python scripts/check_gpu.py
```

## Common Commands

### View logs
```bash
docker compose logs -f        # All services
docker compose logs -f nitk-advisor  # Just the API
```

### Stop the service
```bash
docker compose down
```

### Restart the service
```bash
docker compose restart
```

### Rebuild after code changes
```bash
docker compose down
docker compose build
docker compose up -d
```

### Re-run ingestion (if you add new PDFs)
```bash
# Stop the API first
docker compose down

# Run ingestion (local is faster)
source .venv/bin/activate
python scripts/ingest_documents.py

# Restart API
docker compose up -d
```

### Test retrieval
```bash
docker exec -it nitk-advisor-api python scripts/test_retrieval.py "What is the attendance policy?"
```

### Access container shell
```bash
docker exec -it nitk-advisor-api bash
```

## Production Deployment with Nginx

For production, use the Nginx reverse proxy:

1. **Start with Nginx**:
```bash
docker compose --profile production up -d
```

This will:
- Add rate limiting (10 req/s with burst of 20)
- Add security headers
- Enable gzip compression
- Provide load balancing capability

2. **Access via Nginx**:
- HTTP: http://localhost:80
- API: http://localhost:80/chat

## Environment Variables

Key variables in `.env`:

```bash
# Required
GEMINI_API_KEY=your_api_key_here

# Optional (defaults shown)
API_PORT=8000
LOG_LEVEL=INFO
GEMINI_MODEL=gemini-2.0-flash-exp

# Retrieval tuning
TOP_K_VECTOR=50
TOP_K_BM25=50
TOP_K_HYBRID=100
TOP_K_RERANK=20
FINAL_TOP_K=10
HYBRID_ALPHA=0.3
```

## Data Persistence 

Data is persisted in volumes:
- `./data` - Indices, chunks, PDFs
- `./logs` - Application logs

To backup:
```bash
tar -czf nitk-advisor-data-backup.tar.gz data/
```

To restore:
```bash
tar -xzf nitk-advisor-data-backup.tar.gz
```

## Updating the Application

1. **Pull latest code**:
```bash
git pull
```

2. **Rebuild image**:
```bash
docker compose build
```

3. **Restart service**:
```bash
docker compose up -d
```

Data indices are preserved in the volume.

## Troubleshooting

### "Container is unhealthy"
This usually means ingestion is still running or indices are missing.

```bash
# Check what's happening
docker compose logs

# If ingestion is running, wait for it to complete (1-2 hours on CPU)
# OR stop it and run locally instead:
docker compose down
source .venv/bin/activate
python scripts/ingest_documents.py  # Watch progress in real-time
```

### Container won't start
```bash
# Check logs for errors
docker compose logs

# Verify .env file exists and has GEMINI_API_KEY
cat .env | grep GEMINI_API_KEY

# Ensure you're using correct command (not docker-compose, use docker compose)
docker compose version
```

### 503 Service Unavailable
Indices are missing - run ingestion first:

```bash
# Check if indices exist
ls -la data/bm25_index.pkl data/faiss_storage/

# If missing, stop container and run ingestion
docker compose down
source .venv/bin/activate
python scripts/ingest_documents.py
docker compose up -d
```

### "Address already in use" (port 8000)
```bash
# Check what's using port 8000
sudo lsof -i :8000

# If it's a Docker container:
docker compose down

# If it's a local process:
pkill -f uvicorn  # or kill the specific PID
```

### Out of memory
```bash
# Increase memory limit in compose file (docker-compose.yml)
deploy:
  resources:
    limits:
      memory: 8G  # Increase this
```

### Slow performance
- **Use local ingestion** instead of Docker (2-3x faster, shows progress)
- Consider GPU version for ingestion (10-50x faster)
- For API: increase worker count with gunicorn
- Check resource limits in compose file

### Ingestion taking too long
```bash
# RECOMMENDED: Stop Docker ingestion and run locally instead
docker compose down
source .venv/bin/activate
python scripts/ingest_documents.py  # You'll see progress: "42% | 290/698"

# Or use GPU if available (much faster)
docker compose -f docker-compose.gpu.yml run --rm nitk-advisor-gpu python scripts/ingest_documents.py
```

## Health Checks

Docker automatically monitors health:
```bash
docker ps  # Check HEALTH status column
```

Health check endpoint:
```bash
curl http://localhost:8000/status
```

## Security Notes

1. **Never commit `.env`** - It contains your API key
2. **Use secrets in production** - Consider Docker secrets or vault
3. **Restrict CORS** - Update `src/api/main.py` for production domains
4. **Enable HTTPS** - Uncomment SSL section in nginx.conf
5. **Update base images** - Regularly rebuild for security patches

## Kubernetes Deployment

For K8s deployment, see the generated manifests in `/k8s` (coming soon).

Basic structure:
- Deployment with resource limits
- Service for internal access
- Ingress for external access
- ConfigMap for configuration
- Secret for API keys
- PersistentVolumeClaim for data
