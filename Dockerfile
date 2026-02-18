# Combined Dockerfile: Build frontend + Serve from FastAPI (single container)

# ── Stage 1: Build frontend ──
FROM node:20-alpine AS frontend-build

WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .

ARG VITE_GOOGLE_CLIENT_ID
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID

RUN npm run build

# ── Stage 2: Python backend + frontend dist ──
FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend code (as package)
COPY backend/ ./backend/
COPY project_jarvis/ ./project_jarvis/
COPY skills/ ./skills/

# Copy built frontend into frontend_dist/ (FastAPI serves this)
COPY --from=frontend-build /app/dist ./frontend_dist/

# Remove test files
RUN rm -f backend/test_*.py

# Create data directory
RUN mkdir -p /app/data

ENV PYTHONPATH="/app/project_jarvis:/app"
ENV APP_ENV=production

EXPOSE 8000

# Single process: uvicorn serves API + frontend
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
