# ==============================================================================
# GODBRAIN QUANTUM - Production Dockerfile
# ==============================================================================
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    cmake \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Build C++ Core
WORKDIR /app/core_engine
RUN mkdir -p build && cd build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release && \
    make -j$(nproc)

# Return to app root
WORKDIR /app

# Environment variables will be provided via Kubernetes Secrets
# No hardcoded secrets in Dockerfile

# Expose dashboard port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.connect(('localhost', 8000)); s.close()" || exit 1

# Run god_dashboard.py (Dashboard + Seraph)
CMD ["python", "core/god_dashboard.py"]

