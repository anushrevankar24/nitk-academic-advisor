.PHONY: help build build-gpu up down logs clean test-build

help:
	@echo "NITK Academic Advisor - Docker Commands"
	@echo "========================================"
	@echo "make build      - Build CPU Docker image"
	@echo "make build-gpu  - Build GPU Docker image"
	@echo "make up         - Start services"
	@echo "make down       - Stop services"
	@echo "make logs       - View logs"
	@echo "make clean      - Remove containers and images"
	@echo "make test-build - Test build without running"

build:
	docker compose build

build-gpu:
	docker compose -f docker-compose.gpu.yml build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

clean:
	docker compose down -v
	docker rmi nitk-advisor:latest 2>/dev/null || true

test-build:
	@echo "Testing Docker build..."
	docker compose build --progress=plain
