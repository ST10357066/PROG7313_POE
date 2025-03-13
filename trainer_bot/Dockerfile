# trainer_bot/Dockerfile
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
COPY trainer_bot/trainer_bot.py trainer_bot.py
RUN useradd -m -r appuser && chown appuser:appuser /app
USER appuser
EXPOSE 5006
CMD ["python", "trainer_bot.py"]