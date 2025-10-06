# Multi-stage Dockerfile for Billing System
# Optimized for production deployment with minimal image size

# Stage 1: Builder
FROM python:3.11-slim as builder

# Set build-time arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

# Add metadata
LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.authors="Hendrik Harren" \
      org.opencontainers.image.url="https://github.com/HendrikHarren/project_billing_system_new" \
      org.opencontainers.image.source="https://github.com/HendrikHarren/project_billing_system_new" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.title="Billing System" \
      org.opencontainers.image.description="Automated billing report generation from Google Sheets"

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user for security
RUN groupadd -r billing && useradd -r -g billing billing

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=billing:billing src/ ./src/
COPY --chown=billing:billing test_connection.py ./

# Create cache directory with proper permissions
RUN mkdir -p .cache && chown -R billing:billing .cache

# Create volume mount points
VOLUME ["/app/.cache", "/app/logs"]

# Switch to non-root user
USER billing

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.config.settings import get_config; get_config()" || exit 1

# Default command (can be overridden)
CMD ["python", "-m", "src.cli", "--help"]
