# Dockerfile for Chimera MEV Bot
# Multi-stage build for optimized production image

FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY bot/ ./bot/
COPY config.yaml .
COPY contracts/ ./contracts/

# Create directories for logs and data
RUN mkdir -p /app/logs /app/data

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Development stage (with hot reload support)
FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    flake8 \
    mypy

# Default command for development (can be overridden)
CMD ["python", "-m", "bot.src.main"]

# Production stage (optimized)
FROM base as production

# Run as non-root user for security
RUN useradd -m -u 1000 chimera && \
    chown -R chimera:chimera /app

USER chimera

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run the bot
CMD ["python", "-m", "bot.src.main"]
