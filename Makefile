.PHONY: help install run dev clean reset format lint check test open list-files

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

