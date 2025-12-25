# syntax=docker/dockerfile:1

# ============================================
# RJM Backend Core - Production Dockerfile
# ============================================

FROM python:3.12-slim AS builder

# Install uv for faster dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv (production only, no dev deps)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# ============================================
# Production Stage
# ============================================
FROM python:3.12-slim AS production

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Set PATH to use virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY --chown=appuser:appgroup app/ ./app/
COPY --chown=appuser:appgroup constants.yaml ./
COPY --chown=appuser:appgroup phase_3_docs/ ./phase_3_docs/
COPY --chown=appuser:appgroup rjm_docs/ ./rjm_docs/

# Create logs directory
RUN mkdir -p logs && chown -R appuser:appgroup logs

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Expose port (Render will override via PORT env var)
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/status')" || exit 1

# Run the application
# Render sets PORT env var, so we use shell form to expand it
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}

