FROM python:3.12-slim as builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc postgresql-client libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements-phase5-*.txt ./
RUN pip install --no-cache-dir -r requirements-phase5-*.txt

FROM python:3.12-slim as runtime
WORKDIR /app
RUN useradd -m -u 1000 appuser && apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl && rm -rf /var/lib/apt/lists/*
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY routes_*.py ./
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
CMD ["python", "-m", "uvicorn", "routes_payment:app", "--host", "0.0.0.0", "--port", "8000"]
