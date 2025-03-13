# lean_engine\Dockerfile
# Build stage
FROM python:3.9.7-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Runtime stage
FROM python:3.9.7-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.9/site-packages/ /usr/local/lib/python3.9/site-packages/
COPY lean_engine/lean_service.py lean_service.py
RUN useradd -m -r appuser && chown appuser:appuser /app
USER appuser
EXPOSE 6000
CMD ["python", "lean_service.py"]

