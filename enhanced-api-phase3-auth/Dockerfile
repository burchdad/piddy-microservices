# Multi-stage build for Authentication Service

# Stage 1: Builder
FROM python:3.12-slim as builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements-phase3-auth.txt .
RUN pip install --user --no-cache-dir -r requirements-phase3-auth.txt


# Stage 2: Runtime
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 piddy && mkdir -p /app && chown piddy:piddy /app

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/piddy/.local
ENV PATH=/home/piddy/.local/bin:$PATH

# Copy application code
COPY --chown=piddy:piddy . .

# Switch to non-root user
USER piddy

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Run application
CMD ["uvicorn", "routes_auth:app", "--host", "0.0.0.0", "--port", "8002", "--reload"]
