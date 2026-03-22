# Dockerfile — ChatDEVA Backend
# Used by Railway to build and run the FastAPI service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libsqlite3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install torch CPU-only first (prevents downloading 2GB CUDA version)
RUN pip install --no-cache-dir torch==2.2.0 --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install all other dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full project
COPY . .

# Create necessary directories
RUN mkdir -p /tmp/chatdeva_uploads /tmp/chatdeva_vectors

# Expose port (Railway injects $PORT at runtime)
EXPOSE 8000

# Start command
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
