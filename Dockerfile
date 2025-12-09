# Multi-stage build for optimized Docker image
# Explicitly target linux/amd64 for AWS ECS compatibility
FROM --platform=linux/amd64 python:3.11-slim AS builder

# Set working directory
WORKDIR /app

# Upgrade pip to ensure it can use binary wheels
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies - modern packages have pre-compiled wheels
# This avoids the need for gcc and reduces memory usage during build
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage - target linux/amd64 for AWS ECS
FROM --platform=linux/amd64 python:3.11-slim

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/storage /app/files && \
    chown -R appuser:appuser /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application files
COPY --chown=appuser:appuser main.py .
COPY --chown=appuser:appuser index.html .

# Copy data files
COPY --chown=appuser:appuser files /app/files

# Set environment variables
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8000

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

