# Backend Dockerfile for Render.com
FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy application code (maintain package structure)
COPY backend/ ./backend/
COPY project_jarvis/ ./project_jarvis/
COPY skills/ ./skills/

# Remove dev/test files
RUN rm -f backend/test_*.py

# Create data directory
RUN mkdir -p /app/data

ENV PYTHONPATH="/app/project_jarvis:/app"
ENV APP_ENV=production

EXPOSE 8000

# Shell form so $PORT expands at runtime (Render sets PORT)
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
