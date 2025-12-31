# Dockerfile for DB-RAG Application (API and Workers)
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Flower for Celery monitoring
RUN pip install --no-cache-dir flower

# Copy application code
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
