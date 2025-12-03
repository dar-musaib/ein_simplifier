.PHONY: help install run dev clean reset format lint check test open list-files docker-build docker-up docker-down docker-logs docker-restart docker-shell docker-status

# Variables
PYTHON := python3
PIP := pip3
PORT := 8000
HOST := 0.0.0.0

# File paths - can be overridden via environment variables
SOURCE_FILE ?= files/unique_ein_spons.csv
WORKING_FILE ?= storage/working_data.csv
STORAGE_DIR := storage

# Derive metadata file from working file
WORKING_BASENAME := $(shell basename $(WORKING_FILE) .csv)
WORKING_DIR := $(shell dirname $(WORKING_FILE))
METADATA_FILE := $(WORKING_DIR)/$(WORKING_BASENAME)_metadata.json

# Default target
help:
	@echo "EIN Simplifier - Available commands:"
	@echo ""
	@echo "  make install    - Install Python dependencies"
	@echo "  make run        - Run the FastAPI server"
	@echo "  make dev        - Run server in development mode (auto-reload)"
	@echo "  make clean      - Remove generated files (working file, metadata)"
	@echo "  make reset      - Reset working data (reload from source CSV)"
	@echo "  make format     - Format code with black (if installed)"
	@echo "  make lint       - Lint code with flake8 (if installed)"
	@echo "  make check      - Check if source data file exists"
	@echo "  make list-files - List available source and working files"
	@echo "  make open       - Open frontend in default browser (server must be running)"
	@echo "  make serve-frontend - Serve frontend on port 8080 (alternative method)"
	@echo "  make test       - Run API health check"
	@echo ""
	@echo "Docker commands:"
	@echo "  make docker-build  - Build Docker image"
	@echo "  make docker-up    - Start container"
	@echo "  make docker-down  - Stop and remove container"
	@echo "  make docker-logs  - View container logs"
	@echo "  make docker-restart - Restart container"
	@echo "  make docker-shell - Open shell in running container"
	@echo "  make docker-status - Check container status"
	@echo "  make help       - Show this help message"
	@echo ""
	@echo "File Configuration (via environment variables):"
	@echo "  SOURCE_FILE     - Source CSV file path (default: $(SOURCE_FILE))"
	@echo "  WORKING_FILE    - Working CSV file path (default: $(WORKING_FILE))"
	@echo ""
	@echo "Example:"
	@echo "  SOURCE_FILE=files/data2.csv WORKING_FILE=storage/data2_working.csv make run"

# Install dependencies
install:
	@echo "Installing dependencies..."
	$(PIP) install -r requirements.txt
	@echo "✓ Dependencies installed"

# Run the server
run:
	@echo "Starting FastAPI server on http://$(HOST):$(PORT)"
	@echo "Source file: $(SOURCE_FILE)"
	@echo "Working file: $(WORKING_FILE)"
	@echo "API docs available at http://localhost:$(PORT)/docs"
	SOURCE_FILE=$(SOURCE_FILE) WORKING_FILE=$(WORKING_FILE) $(PYTHON) main.py

# Run in development mode with auto-reload
dev:
	@echo "Starting FastAPI server in development mode (auto-reload)"
	@echo "Source file: $(SOURCE_FILE)"
	@echo "Working file: $(WORKING_FILE)"
	@echo "API docs available at http://localhost:$(PORT)/docs"
	SOURCE_FILE=$(SOURCE_FILE) WORKING_FILE=$(WORKING_FILE) uvicorn main:app --host $(HOST) --port $(PORT) --reload

# Clean generated files
clean:
	@echo "Cleaning generated files..."
	@echo "Working file: $(WORKING_FILE)"
	@echo "Metadata file: $(METADATA_FILE)"
	@if [ -f $(WORKING_FILE) ]; then \
		rm $(WORKING_FILE) && echo "✓ Removed $(WORKING_FILE)"; \
	fi
	@if [ -f $(METADATA_FILE) ]; then \
		rm $(METADATA_FILE) && echo "✓ Removed $(METADATA_FILE)"; \
	fi
	@echo "✓ Clean complete"

# Reset working data (reload from source)
reset: clean
	@echo "Working data will be reset on next server start"
	@echo "Run 'make run' or 'make dev' to reload from source CSV"

# Format code (requires black)
format:
	@if command -v black > /dev/null; then \
		echo "Formatting code with black..."; \
		black main.py; \
		echo "✓ Formatting complete"; \
	else \
		echo "⚠ black not installed. Install with: pip install black"; \
	fi

# Lint code (requires flake8)
lint:
	@if command -v flake8 > /dev/null; then \
		echo "Linting code with flake8..."; \
		flake8 main.py --max-line-length=100 --ignore=E501,W503; \
		echo "✓ Linting complete"; \
	else \
		echo "⚠ flake8 not installed. Install with: pip install flake8"; \
	fi

# Check if source data exists
check:
	@if [ -f $(SOURCE_FILE) ]; then \
		echo "✓ Source file found: $(SOURCE_FILE)"; \
		wc -l $(SOURCE_FILE) | awk '{print "  Lines:", $$1}'; \
	else \
		echo "✗ Source file not found: $(SOURCE_FILE)"; \
		echo "  Please ensure the source CSV file exists in the files/ directory"; \
		exit 1; \
	fi

# Open frontend in browser (requires server to be running)
open:
	@echo "Opening frontend..."
	@echo "Make sure the server is running first (make dev or make run)"
	@if command -v open > /dev/null; then \
		open http://localhost:$(PORT); \
	elif command -v xdg-open > /dev/null; then \
		xdg-open http://localhost:$(PORT); \
	else \
		echo "Please open http://localhost:$(PORT) in your browser"; \
	fi

# Serve frontend with simple HTTP server (alternative method)
serve-frontend:
	@echo "Serving frontend on http://localhost:8080"
	@echo "Note: Make sure the API server is running on port 8000"
	@echo "Press Ctrl+C to stop"
	@if command -v python3 > /dev/null; then \
		cd . && python3 -m http.server 8080; \
	else \
		echo "Python 3 not found. Please use 'make dev' and open http://localhost:$(PORT)"; \
	fi

# List available source and working files
list-files:
	@echo "Available source files:"
	@if [ -d files ]; then \
		find files -name "*.csv" -type f 2>/dev/null | head -20 || echo "  No CSV files found in files/"; \
	else \
		echo "  files/ directory not found"; \
	fi
	@echo ""
	@echo "Available working files:"
	@if [ -d $(STORAGE_DIR) ]; then \
		find $(STORAGE_DIR) -name "*_working.csv" -o -name "working_*.csv" -type f 2>/dev/null | head -20 || echo "  No working files found"; \
	else \
		echo "  $(STORAGE_DIR)/ directory not found"; \
	fi

# Test API health
test:
	@echo "Testing API health..."
	@if command -v curl > /dev/null; then \
		curl -s http://localhost:$(PORT)/ | python3 -m json.tool || echo "✗ Server not running"; \
	else \
		echo "⚠ curl not available. Please test manually at http://localhost:$(PORT)/"; \
	fi

# Docker commands (using plain Docker, not docker-compose)
CONTAINER_NAME := ein-simplifier
IMAGE_NAME := ein-simplifier
PORT := 8000

docker-build:
	@echo "Building Docker image..."
	@if command -v docker > /dev/null; then \
		docker build -t $(IMAGE_NAME) .; \
		echo "✓ Image built successfully"; \
	else \
		echo "✗ Docker not found. Please install Docker."; \
		exit 1; \
	fi

docker-up:
	@echo "Starting container..."
	@if command -v docker > /dev/null; then \
		if docker ps -a --format '{{.Names}}' | grep -q "^$(CONTAINER_NAME)$$"; then \
			echo "Removing existing container..."; \
			docker rm -f $(CONTAINER_NAME) 2>/dev/null || true; \
		fi; \
		if [ -f .env ]; then \
			export $$(cat .env | grep -v '^#' | xargs); \
		fi; \
		docker run -d \
			--name $(CONTAINER_NAME) \
			--restart unless-stopped \
			-p $(PORT):8000 \
			-v "$(PWD)/storage:/app/storage" \
			-v "$(PWD)/files:/app/files" \
			-e HOST=0.0.0.0 \
			-e PORT=8000 \
			-e WORKERS=$${WORKERS:-4} \
			-e RELOAD=$${RELOAD:-false} \
			-e LOG_LEVEL=$${LOG_LEVEL:-info} \
			-e CORS_ORIGINS="$${CORS_ORIGINS:-*}" \
			-e STORAGE_DIR=/app/storage \
			-e SOURCE_FILE=/app/files/unique_ein_spons.csv \
			-e WORKING_FILE=/app/storage/working_data.csv \
			$(IMAGE_NAME); \
		echo "✓ Container started on port $(PORT)"; \
		echo "  Access at: http://localhost:$(PORT)"; \
	else \
		echo "✗ Docker not found. Please install Docker."; \
		exit 1; \
	fi

docker-down:
	@echo "Stopping container..."
	@if command -v docker > /dev/null; then \
		docker stop $(CONTAINER_NAME) 2>/dev/null || echo "Container not running"; \
		docker rm $(CONTAINER_NAME) 2>/dev/null || echo "Container not found"; \
		echo "✓ Container stopped and removed"; \
	else \
		echo "✗ Docker not found. Please install Docker."; \
		exit 1; \
	fi

docker-logs:
	@echo "Viewing container logs (Ctrl+C to exit)..."
	@if command -v docker > /dev/null; then \
		docker logs -f $(CONTAINER_NAME) 2>/dev/null || echo "✗ Container not found. Start it with: make docker-up"; \
	else \
		echo "✗ Docker not found. Please install Docker."; \
		exit 1; \
	fi

docker-restart:
	@echo "Restarting container..."
	@if command -v docker > /dev/null; then \
		$(MAKE) docker-down; \
		$(MAKE) docker-up; \
		echo "✓ Container restarted"; \
	else \
		echo "✗ Docker not found. Please install Docker."; \
		exit 1; \
	fi

docker-shell:
	@echo "Opening shell in container..."
	@if command -v docker > /dev/null; then \
		docker exec -it $(CONTAINER_NAME) /bin/bash || docker exec -it $(CONTAINER_NAME) /bin/sh || echo "✗ Container not running. Start it with: make docker-up"; \
	else \
		echo "✗ Docker not found. Please install Docker."; \
		exit 1; \
	fi

docker-status:
	@echo "Container status:"
	@if command -v docker > /dev/null; then \
		if docker ps --format '{{.Names}}' | grep -q "^$(CONTAINER_NAME)$$"; then \
			echo "✓ Container is running"; \
			docker ps --filter "name=$(CONTAINER_NAME)" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"; \
		else \
			echo "✗ Container is not running"; \
		fi; \
	else \
		echo "✗ Docker not found. Please install Docker."; \
		exit 1; \
	fi

