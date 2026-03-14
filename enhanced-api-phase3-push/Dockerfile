# Push Notification Service Multi-stage Build

FROM python:3.12-slim as builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt


FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 piddy && mkdir -p /app && chown piddy:piddy /app

WORKDIR /app

COPY --from=builder /root/.local /home/piddy/.local
ENV PATH=/home/piddy/.local/bin:$PATH

COPY --chown=piddy:piddy . .

USER piddy

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8005/health || exit 1

CMD ["uvicorn", "routes_push:app", "--host", "0.0.0.0", "--port", "8005"]
