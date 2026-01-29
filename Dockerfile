FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir .

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/fulcrum

# Expose API port
EXPOSE 8000

# Start command using uvicorn
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
