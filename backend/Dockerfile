# Use Python 3.11 slim image
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY .env.example ./.env

# Change ownership to app user
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/v1/health || exit 1

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]

# Development stage
FROM base as development

USER root
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt

USER appuser

# Override CMD for development
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]

# Testing stage
FROM development as testing

USER root
COPY requirements-test.txt .
RUN pip install -r requirements-test.txt

# Copy test files
COPY tests/ ./tests/
COPY pyproject.toml .

USER appuser

# Override CMD for testing
CMD ["pytest", "-v", "--cov=src", "--cov-report=xml"]