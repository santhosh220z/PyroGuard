# PyroGuard Dockerfile - Multi-stage build
# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app
COPY "pyroguard ui/package*.json" "pyroguard ui/"
RUN cd "pyroguard ui" && npm ci

COPY "pyroguard ui/" "pyroguard ui/"
RUN cd "pyroguard ui" && npm run build

# Stage 2: Python backend
FROM python:3.11-slim AS backend

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r pyroguard && useradd -r -g pyroguard -u 1000 pyroguard

WORKDIR /app

# Copy Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY configs/ ./configs/
COPY scripts/ ./scripts/

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/pyroguard ui/dist ./pyroguard ui/dist

# Create directories for data
RUN mkdir -p /app/data/incidents/snapshots /app/models /app/datasets/processed /app/runs && \
    chown -R pyroguard:pyroguard /app

# Switch to non-root user
USER pyroguard

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health/ready', timeout=5).raise_for_status()" || exit 1

# Expose port
EXPOSE 8000

# Run
CMD ["python", "-m", "app.main"]